'''
CDN Analysis

python cdnanalysis.py -i top-1m.csv -c cdnproviders.csv -o opcdn -t 500
'''
import sys
import getopt
import os
from subprocess import check_output
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from StringIO import StringIO
from tabulate import tabulate

num_experiments = 10
dns_server = '8.8.8.8:53'


def get_timing(cdn_domain_list, ofile):
    '''
    Get mean time to first byte for the sites served by top CDNs.
    Try the different prefixes to form url. If curl feteches any of these
    successfully, then run the experiments num_experiments times.
    Store details of each run of experiments in pretty formatted table as .txt
    file. Store the min, mean, max information per CDN in .csv file.
    Display the same information as box plots in .png file.
    '''
    prefixes = ['http://', 'http://www.', 'https://', 'https://www.']
    df_columns = ['CDN', 'Domain', 'URL', 'Namelookup', 'Connect',
                  'Appconnect', 'Pretransfer', 'Starttransfer', 'Total']
    df = pd.DataFrame(columns=df_columns)
    for cdn_name, domain_list in cdn_domain_list:
        for domain in domain_list:
            for prefix in prefixes:
                url = prefix + domain
                try:
                    print 'Trying: ' + url
                    c_output = check_output(['curl', '-s', '-o', '/dev/null',
                                             '-H', '"Pragma:no-cache"',
                                             '-H', '"Cache-Control: no-cache"',
                                             url, '-w'
                                             '%{http_code},'
                                             '%{time_namelookup},'
                                             '%{time_connect},'
                                             '%{time_appconnect},'
                                             '%{time_pretransfer},'
                                             '%{time_starttransfer},'
                                             '%{time_total}'])
                    times = c_output.split(',')
                    status_code = times[0]
                    if (status_code.startswith('2')):
                        print 'Success ' + status_code + ': ' + url
                        for x in range(num_experiments):
                            c_str = check_output(['curl', '-s', '-o',
                                                  '/dev/null',
                                                  '-H', '"Pragma:no-cache"',
                                                  '-H',
                                                  '"Cache-Control: no-cache"',
                                                  url, '-w'
                                                  '%{time_namelookup},'
                                                  '%{time_connect},'
                                                  '%{time_appconnect},'
                                                  '%{time_pretransfer},'
                                                  '%{time_starttransfer},'
                                                  '%{time_total}'])
                            dfstring = cdn_name + ',' + domain + ',' + url \
                                + ',' + c_str
                            text = StringIO(dfstring)
                            newdf = pd.read_csv(text, names=df_columns)
                            df = df.append(newdf, ignore_index=True)
                        break
                    elif (status_code.startswith('3')):
                        print 'Redirected ' + status_code + ': ' + url
                    elif (status_code.startswith('4')):
                        print 'Error ' + status_code + ': ' + url
                    else:
                        print 'Unhandled status code ' + status_code + ': ' \
                              + url
                except:
                    print 'Execption in: ' + url

        '''
        It is not clear whether in curl output, connect time includes
        namelookup time and so on.
        I assumed it does not and took the values directly to represent each
        stage.
        Following code could be used instead if the assumption is incorrect
        df['DNS'] = df['Namelookup']
        df['TCP'] = df['Connect'] - df['Namelookup']
        df['SSL'] = df['Appconnect'] - df['Connect']
        df['TTFB'] = df['Starttransfer']
        '''
    with open(ofile+'.txt', 'w') as outputfile:
        outputfile.write(tabulate(df, headers='keys', tablefmt='psql'))

    df2 = df.groupby(['CDN', 'Domain', 'URL']).agg([np.min, np.mean, np.max])
    output_csv = ofile + '.csv'
    df2.to_csv(output_csv, mode='w')
    plt.figure()
    df.boxplot(column=['Namelookup', 'Connect', 'Appconnect',
                       'Starttransfer'], by='CDN')
    plt.savefig(ofile+'.png')


def get_cdns(cfile):
    '''
    Get list of CDNs and the domain associated with them.
    '''
    endl = os.linesep
    with open(cfile) as cdnfile:
        lines = cdnfile.readlines()
    cdn_list = [tuple(line.strip(endl).strip().split(',')) for line in lines]
    return cdn_list


def is_cdn(domain, cdnList):
    '''
    Check if a domain name contains a string associated with CDN domain.
    This could be done more efficiently by preprocessing the strings
    associated with CDNs into a Aho-Corasick Trie (which is great for
    multi-pattern string search).
    '''
    for cdn in cdnList:
        if cdn[0] in domain:
            return (True, cdn[1])
    return (False, '')


def get_cdn_domains(domain, cdnList):
    '''
    Run dig and check if either the domain name or the domains
    returned as CNAME are associated with well-known CDNS.
    '''
    endl = os.linesep
    try:
        dig_output = check_output(['dig', domain, dns_server])
        pretty_dig_output = dig_output.split(endl)
        (iscdn, cdnname) = is_cdn(domain, cdnList)
        if iscdn:
            print 'CDN Domain: ', domain
            return cdnname
        else:
            for line in pretty_dig_output:
                if 'CNAME' in line:
                    (iscdn, cdnname) = is_cdn(line, cdnList)
                    if iscdn:
                        print 'CDN CNAME: ', line, domain
                        return cdnname
    except:
        print 'Exception in dig for: ' + domain
    return ''


def get_top_sites(ifile, threshold):
    '''
    Get top threshold number of sites from the file containing
    top sites from Alexa.
    '''
    endl = os.linesep

    with open(ifile) as infile:
        head = [tuple(next(infile).strip(endl).split(','))
                for x in xrange(threshold)]

    return head


def usage(pgm):
    '''Print usage message.'''
    print 'Usage: %s -i <inputfile> -c <cdnfile> -o <outputfile> ' \
          '-t <threshold>' % pgm


def main(argv):
    inputfile = ''
    cdnfile = ''
    outputfile = ''
    threshold = 0

    '''
    Parse command line option

    * inputfile: csv file containing the alexa top 1M sites/domains
    * cdnfile: csv file containing the domains used by well-known CDNs
    * outputfile: txt file containing output of cdn analysis, a csv file is
    *             also generated with same prefix showing averages
    * threshold: number of top sites/domains to consider
    '''
    try:
        opts, args = getopt.getopt(argv[1:],
                                   'hi:c:o:t:',
                                   ['ifile=', 'cfile=', 'ofile=',
                                    'threshold='])
    except getopt.GetoptError:
        usage(argv[0])
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            usage(arg[0])
            sys.exit()
        elif opt in ('-i', '--ifile'):
            inputfile = arg
        elif opt in ('-c', '--cfile'):
            cdnfile = arg
        elif opt in ('-o', '--ofile'):
            outputfile = arg
        elif opt in ('-t', '--threshold'):
            threshold = int(arg)

    print 'Input file is ', inputfile
    print 'CDN file is ', cdnfile
    print 'Output file is ', outputfile
    print 'Threshold is ', str(threshold), '\n'
    if inputfile == '' or cdnfile == '' or outputfile == '' or threshold <= 0:
        usage(argv[0])
        sys.exit(2)
    cdn_list = get_cdns(cdnfile)
    top_sites = get_top_sites(inputfile, threshold)
    cdn_domain = dict()
    for rank, domain in top_sites:
        cdnname = get_cdn_domains(domain, cdn_list)
        if (cdnname != ''):
            cdn_domain.setdefault(cdnname, list()).append(domain)

    cdn_domain_list = [(k, v) for k, v in cdn_domain.iteritems()]
    sorted_cdn_domain_list = sorted(cdn_domain_list, key=lambda t: len(t[1]),
                                    reverse=True)

    print '\n{CDN: DomainName}'
    print sorted_cdn_domain_list
    print '\n'
    get_timing(sorted_cdn_domain_list, outputfile)

if __name__ == '__main__':
    main(sys.argv[:])
