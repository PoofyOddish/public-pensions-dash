#Load data from Boston College's Public Pension Database (PPD)
#API Documentation found here: https://publicplansdata.org/public-plans-database/api/
#Data dictionary found here: https://publicplansdata.org/public-plans-database/documentation/

#Import needed packages
import pandas as pd
import requests
import urllib

#Define list of variables to be called from PPD API
var_list = "fy,PlanName,StateAbbrev,ActFundedRatio_GASB,PercentReqContPaid,InvestmentReturnAssumption_GASB,InvestmentReturn_1yr,InvestmentReturn_5yr,InvestmentReturn_10yr,TotMembership,StateName"

#Create dictionary to feed into query
params = {'q':'QVariables','&variables':var_list,'format':'json'}
          
#Access PPD API using requests
r = requests.get('http://publicplansdata.org/api/?q=QVariables&variables='
                 +urllib.parse.unquote(var_list)+"&format=json")

#Convert JSON file from PPD to Pandas DF
data = pd.DataFrame.from_dict(r.json()[1:])
data.columns = map(str.lower, data.columns)