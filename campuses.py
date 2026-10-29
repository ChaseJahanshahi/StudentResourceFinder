"""Explicit campus identities. A recognized domain identifies a source, not eligibility."""
import re

# UC domains checked against the UC campus directory; CSU entries against CSU's.
# This is a starter autocomplete, not a claim to list every California college.
CAMPUS_ROWS = [
    ('University of California, Los Angeles', 'UCLA', 'ucla.edu', 'UC', 'Los Angeles'),
    ('University of California, Irvine', 'UCI', 'uci.edu', 'UC', 'Irvine'),
    ('University of California, Berkeley', 'UC Berkeley', 'berkeley.edu', 'UC', 'Berkeley'),
    ('University of California, Davis', 'UC Davis', 'ucdavis.edu', 'UC', 'Davis'),
    ('University of California, San Diego', 'UCSD', 'ucsd.edu', 'UC', 'San Diego'),
    ('University of California, Santa Barbara', 'UCSB', 'ucsb.edu', 'UC', 'Santa Barbara'),
    ('University of California, Santa Cruz', 'UCSC', 'ucsc.edu', 'UC', 'Santa Cruz'),
    ('University of California, Riverside', 'UCR', 'ucr.edu', 'UC', 'Riverside'),
    ('University of California, Merced', 'UC Merced', 'ucmerced.edu', 'UC', 'Merced'),
    ('University of California, San Francisco', 'UCSF', 'ucsf.edu', 'UC', 'San Francisco'),
    ('San Diego State University', 'SDSU', 'sdsu.edu', 'CSU', 'San Diego'),
    ('San Francisco State University', 'SFSU', 'sfsu.edu', 'CSU', 'San Francisco'),
    ('San José State University', 'SJSU', 'sjsu.edu', 'CSU', 'San Jose'),
    ('California State University, Long Beach', 'CSULB', 'csulb.edu', 'CSU', 'Long Beach'),
    ('California State University, Fullerton', 'CSUF', 'fullerton.edu', 'CSU', 'Fullerton'),
    ('California State University, Northridge', 'CSUN', 'csun.edu', 'CSU', 'Northridge'),
    ('California State University, Los Angeles', 'Cal State LA', 'calstatela.edu', 'CSU', 'Los Angeles'),
    ('California State University, Sacramento', 'Sacramento State', 'csus.edu', 'CSU', 'Sacramento'),
    ('California State University, San Bernardino', 'CSUSB', 'csusb.edu', 'CSU', 'San Bernardino'),
    ('California State University, San Marcos', 'CSUSM', 'csusm.edu', 'CSU', 'San Marcos'),
    ('California State Polytechnic University, Pomona', 'Cal Poly Pomona', 'cpp.edu', 'CSU', 'Pomona'),
]
CAMPUS_SOURCES = ['https://www.universityofcalifornia.edu/about-uc/campuses-locations',
                  'https://www.calstate.edu/attend/campuses']
CAMPUS_LIST = [dict(name=n, short=s, domain=d, college_type=t, city=c) for n,s,d,t,c in CAMPUS_ROWS]

def normalized(value):
    return re.sub(r'[^a-z0-9]', '', value.lower().replace('é', 'e'))

def resolve_campus(value):
    needle = normalized(value or '')
    if not needle:
        return None
    for campus in CAMPUS_LIST:
        aliases = (campus['name'], campus['short'], campus['domain'], campus['name'].replace('University of California,', 'UC'))
        if needle in {normalized(alias) for alias in aliases}:
            return dict(campus)
    return None

def campus_from_host(host):
    return next((dict(c) for c in CAMPUS_LIST if host == c['domain'] or host.endswith('.'+c['domain'])), None)
