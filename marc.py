"""
This takes a MARCXML filename as an argument and converts it into
MARC records for the unglued pandata (in .xml and .mrc formats).
Consider it a catalogolem: http://commons.wikimedia.org/wiki/File:Arcimboldo_Librarian_Stokholm.jpg
Use the MARCXML file for the non-unglued pandata from Library of Congress.
"""

import pymarc
import logging
from datetime import datetime
from StringIO import StringIO

import licenses

marc_rels = {
    'aut': 'author',
    'edc': 'editor_of_a_compilation', 
    'ill': 'illustrator',
    'trl': 'translator',
    }
marc_rels_plural = {
    'aut': 'authors',
    'edc': 'editors_of_a_compilation', 
    'ill': 'illustrators',
    'trl': 'translators',
    }

main_entries = ['aut', 'edc', 'trl', 'ill']

# argument is a dict with all the metadata from the pandata.yaml file
def stub(pandata):
    
    record = pymarc.Record(force_utf8=True)

    now = datetime.now()
    
    #mostly to identify this record as a 'stub'
    record.add_ordered_field( pymarc.Field(tag='001', data='stb'+now.strftime('%y%m%d%H%M%S')))
    
    add_stuff(record)
    
    # fun fun fun 008
    new_field_value= now.strftime('%y%m%d')+'s'
    publication_date = pandata.issued_gutenberg  # library cataloging will consider "Project Gutenberg" to be the publisher of the edition
    if publication_date and len(publication_date)>3: # must be at least a year
        new_field_value += publication_date[0:4]
    else:
        new_field_value += '||||'
    new_field_value += '||||xx |||||o|||||||||||eng||'
    record.add_ordered_field(pymarc.Field(tag='008', data=new_field_value))   
    
    identifiers = pandata.identifiers
    # add IBSNs if available
    isbn = identifiers.get('isbn', None) # most isbns in PG are really for related editions
    if isbn:
        record.add_ordered_field( 
            pymarc.Field(
                tag='020',
                indicators = [' ', ' '],
                subfields = ['a', isbn]
            )
        )
    related = identifiers.get('isbns_related', []) 
    for isbn in related:
        record.add_ordered_field( 
            pymarc.Field(
                tag='020',
                indicators = [' ', ' '],
                subfields = ['a', isbn + ' (related)']
            )
        )
        
    # OCLC number
    oclc = identifiers.get('oclc', None)
    if oclc:
        record.add_ordered_field(
            pymarc.Field(
                tag='035',
                indicators = [' ', ' '],
                subfields = ['a', '(OCoLC)' + str(oclc)]
            )
        )
        
    # contributors 
    # use marc codes from http://www.loc.gov/marc/relators/relaterm.html
    contributors = []
    # hueristically decide the "main entry", the first contributor
    for marc_type in main_entries:
        for contributor in pandata.agents(marc_rels_plural[marc_type]):
            contributors.append( (marc_type, contributor) )

    if contributors:
        record.add_ordered_field( 
            pymarc.Field(
                tag='100',
                indicators = ['1', ' '],
                subfields = [
                    'a', contributors[0][1].get( marc_rels[contributors[0][0]]+'_sortname',''),
                    '4', contributors[0][0],
                ]
            )
        )
    
    #language
    print pandata.language
    if pandata.language:
        is_translation = '1' if pandata.translators else '0'
        record.add_ordered_field( 
            pymarc.Field(
                tag='041',
                indicators = [is_translation, 'iso639-1'],
                subfields = ['a', pandata.language ]
            )
        )
    
    if len(contributors)>1:
        for contributor in contributors[1:]:
            record.add_ordered_field(
                pymarc.Field(
                    tag='700',
                    indicators = ['1', ' '],
                    subfields = [
                        'a', contributor[1].get(marc_rels[contributor[0]]+'_sortname',''),
                        'e', marc_rels[contributor[0]].replace('_',' ')+'.',
                        '4', contributor[0],
                    ]
                )
            )

    # add subfield to 245 indicating format
    record.add_ordered_field(
        pymarc.Field(
            tag='245',
            indicators = ['1', '0'],
            subfields = [
                'a', pandata.title,
                'a', '[electronic resource]',
            ]
        )
    )
    
    # publisher, date
    if pandata.publisher:
        field260 = pymarc.Field(
            tag='260',
            indicators = [' ', ' '],
            subfields = [
                'b', pandata.publisher,
            ]
        )
        if publication_date:
            field260.add_subfield('c', unicode(publication_date))
        record.add_ordered_field(field260)
        
    if pandata.description:
        #add 520 field (description)
        field520 =  pymarc.Field(
            tag='520',
            indicators = [' ', ' '],
            subfields = [
                'a', pandata.description,
            ]
        )
        record.add_ordered_field(field520)
        
    add_license(record, pandata)
    
    return record

def add_license(record, pandata):
    if pandata.rights:
        # add 536 field (funding information)
        record.add_ordered_field(
            pymarc.Field(
                tag='536',
                indicators = [' ', ' '],
                subfields = [ 'a', pandata.funding_info,],
            )
        )
    
        # add 540 field (terms governing use)
        field540 = pymarc.Field(
            tag='540',
            indicators = [' ', ' '],
            subfields = [
                'a', dict(licenses.CHOICES).get(pandata.rights,pandata.rights),
            ]
        )
        rights_url = pandata.rights_url if pandata.rights_url else dict(licenses.GRANTS).get(pandata.rights,None)
        if rights_url:
            field540.add_subfield('u', rights_url)
        record.add_ordered_field(field540)

def add_stuff(record):
    # add field indicating record originator
    record.add_ordered_field( pymarc.Field(tag='003', data='GITenberg'))
    
    # update timestamp of record
    datestamp = datetime.now().strftime('%Y%m%d%H%M%S') + '.0'
    record.add_ordered_field( pymarc.Field(tag='005', data=datestamp))

    # change 006, 007 because this is an online resource
    record.add_ordered_field(pymarc.Field(tag='006',data='m     o  d        '))
    record.add_ordered_field(pymarc.Field(tag='007',data='cr'))
