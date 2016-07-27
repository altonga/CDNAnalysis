# CDNAnalysis
Analysis of CDNs used by top sites as per Alexa. 

I used as input a mapping file which associates domains with the CDNs. 

Command: python cdnanalysis.py -i top-1m.csv -c cdnproviders.csv -o opcdn -t 500

For the top 500 Alexa websites, I could extract infomation for only 2 CDNs 
-- ChinaCache and Google. Following are the observations from an experiment 
run 10 times to obtain the time split:

1. For ChinaCache, the connect is much larger than for Google. This indicates 
that ChinaCache servers are located far away geographically (mostly in China).

2. Appconnect is high for Google as it uses SSL while ChinaCache doesn't.
 
3. Overall, Time To First Byte is much higher for ChinaCache as compared to Google.




