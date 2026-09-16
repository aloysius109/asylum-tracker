

# -*- coding: utf-8 -*-
"""
Created on Tue June 11 2024

@author: Kathryn Hopkins
"""
'''
This code analyses and presents the UNHCR's asylum seeker data from 2000 to 2023. The queries used are downloadable at:
A. Asylum Applications
https://www.unhcr.org/refugee-statistics/download/?url=aj1GG7
B. Asylum Decisions
https://www.unhcr.org/refugee-statistics/download/?url=837ayH
'''
#%%
# Data was downloaded from the year 2000 onwards
# At the time of downloading, data was available to June 2023
# 2023 is therefore a half-year of data, whilst all other years are full calendar years
#%%Preliminaries
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib import style
import matplotlib.ticker as mtick
from matplotlib.ticker import StrMethodFormatter
mpl.rcParams.update(mpl.rcParamsDefault)
#%% Function to calculate percentages for pie charts
def func(pct, allvalues):
    absolute = int(pct / 100.*np.sum(allvalues))
    return "{:.1f}%".format(pct, absolute)
#%%Import Applications data downloaded from UNHCR website
UNapps=pd.read_csv('asylum-applications.csv')
# Perform checks on the data
UNapps.head(10)
UNapps.describe()
UNapps.shape
UNapps.axes
UNapps.info()
UNapps['Country of asylum (ISO)'].value_counts(dropna=False)
UNapps['Country of asylum (ISO)'].unique()
#%%Check UK application  volumes for 2023 and 2022
UK = UNapps.loc[(UNapps['Country of asylum (ISO)']=='GBR') & (UNapps['Year']==2023)]
UK['applied'].sum()
UK['applied']
UK = UNapps.loc[(UNapps['Country of asylum (ISO)']=='GBR') & (UNapps['Year']==2022)]
UK['applied'].sum()
#%%Import Decisions Data
UNdecs=pd.read_csv('asylum-decisions.csv')
UNdecs.head()
#%%Sum the decision data to check for summing anomalies at source
UNdecs['Total decisions02'] = UNdecs.loc[:,['Recognized decisions' ,'Complementary protection','Rejected decisions','Otherwise closed']].sum(axis = 1)
UNdecs['Total decisions CHECK'] = UNdecs['Total decisions']-UNdecs['Total decisions02']
UNdecs['Total decisions CHECK'].sum()# There is a slight adding error in the UN's data so replace their 'Total Decisions' column with a new one
UNdecs['Total decisions'] = UNdecs.loc[:,['Recognized decisions' ,'Complementary protection','Rejected decisions','Otherwise closed']].sum(axis = 1)
# And delete the checking columns
UNdecs.drop(['Total decisions02', 'Total decisions CHECK'], axis = 1, inplace = True)
# Check which columns remain
UNdecs.columns
#%% Check UK figures
UK = UNdecs.loc[(UNdecs['Country of asylum (ISO)']=='GBR') & (UNdecs['Year']==2023)]
UK['Total decisions'].sum()
UK = UNdecs.loc[(UNdecs['Country of asylum (ISO)']=='GBR') & (UNdecs['Year']==2022)]
UK['Total decisions'].sum()
#%% Group applications and decisions by Year of Application. This sums the different types of applications and decisions and the different authority types, as well as the case type, for each country of origin & country of application, by year. The result is an overall aggregate of applications from each country and decisions made in each country by year. Note that no differentiation is made between persons and cases - some countries report by person, and some by case. Some countries administer more than one person per application, whilst other countries administer only one person per application. Thus, the data in this project refers to the administrative caseload rather than a count of individuals applying for asylum. To calculate the total number of individuals applying, uplifts should be added to cases where there is, on average, more than one person per case. The multipliers for transforming cases to individuals may differ from country to country and can be found in the UNHCR's documentation.
# Group applications
UNapps=UNapps.groupby(['Year', 'Country of origin (ISO)', 'Country of asylum (ISO)']).agg({'applied':np.sum})
# Group decisions
UNdecs=UNdecs.groupby(['Year', 'Country of origin (ISO)', 'Country of asylum (ISO)']).agg({'Recognized decisions':np.sum, 'Complementary protection':np.sum, 'Rejected decisions':np.sum, 'Otherwise closed':np.sum, 'Total decisions':np.sum})
#%%Calculate grant rates using the decision data. This is achieved by dividing each type of decision by the total number of decisions made.
# Positive asylum decisions ('Granted')
UNdecs['Granted']=UNdecs['Recognized decisions']/UNdecs['Total decisions']
# Humanitarian protection ('Other protection')
UNdecs['Other protection']=UNdecs['Complementary protection']/UNdecs['Total decisions']
# Negative asylum decisions ('Refused')
UNdecs['Refused']=UNdecs['Rejected decisions']/UNdecs['Total decisions']
# Cases closed without a decision ('Otherwise closed')
UNdecs['Otherwise Closed']=UNdecs['Otherwise closed']/UNdecs['Total decisions']
#Check that the percentages sum to 100%
UNdecs['Total%'] = UNdecs.loc[:,['Granted' ,'Other protection','Refused',
      'Otherwise Closed']].sum(axis = 1)
UNdecs['Total%'].sum()
UNdecs['Total%'].dtypes
# Some of the rows don't sum to 100% - check these
UNdecsCheckTotal = UNdecs[UNdecs['Total%'] != 1.0]
# 1552 rows don't sum properly, some are due to n/a values across the row, the others are 
len(UNdecsCheckTotal)
len(UNdecs)
UNdecs.shape
# Drop checking column after checking
UNdecs.drop('Total%', axis = 1, inplace = True)
#%%Join Apps and Decs Datasets together
UNTotalAppsDecs=pd.merge(UNapps, UNdecs, how = 'left', left_index=True, right_index=True)
UNTotalAppsDecs.head()
#and reset the index
UNTotalAppsDecs.reset_index(inplace=True)
# Reset UNapps index so it can be used later
UNapps.reset_index(inplace = True)
#Reset index for later
UNdecs.reset_index(inplace = True)
#Check the application and decision volumes again
UK = UNTotalAppsDecs.loc[(UNTotalAppsDecs['Country of asylum (ISO)']=='GBR') & (UNTotalAppsDecs['Year']==2023)]
UK['applied'].sum()
UK['Total decisions'].sum()
UK = UNTotalAppsDecs.loc[(UNTotalAppsDecs['Country of asylum (ISO)']=='GBR') & (UNTotalAppsDecs['Year']==2022)]
UK['applied'].sum()
UK['Total decisions'].sum()
#%% Create Receiving Country dataset (removes country of origin)
UNTotalAppsDecs = UNTotalAppsDecs.groupby(['Year', 'Country of asylum (ISO)']).agg({'applied':np.sum, 'Recognized decisions':np.sum, 'Complementary protection':np.sum, 'Rejected decisions':np.sum, 'Otherwise closed':np.sum, 'Total decisions':np.sum})
#%%Create new columns in the Receiving Country dataset
UNTotalAppsDecs['Backlog']=UNTotalAppsDecs['Total decisions']-UNTotalAppsDecs['applied']
UNTotalAppsDecs['FVP']=UNTotalAppsDecs['Total decisions']/UNTotalAppsDecs['applied']
UNTotalAppsDecs.reset_index(inplace=True)
#%% Create 2017 Onwards dataset (to get application volumes recently)
UNTotalAppsDecs2017On=UNTotalAppsDecs[(UNTotalAppsDecs['Year']==2017)|(UNTotalAppsDecs['Year']==2018)|
        (UNTotalAppsDecs['Year']==2019)|
        (UNTotalAppsDecs['Year']==2020)|
        (UNTotalAppsDecs['Year']==2021)|
        (UNTotalAppsDecs['Year']==2022)|
        (UNTotalAppsDecs['Year']==2023)]
# Create a list of all countries in the dataset
TotalCountries = UNTotalAppsDecs2017On['Country of asylum (ISO)'].unique().tolist()
#%% =============================================================================
#Calculate the Top 20 application volumes from 2017 onwards
# =============================================================================
UNTotalAppsDecs2017On = UNTotalAppsDecs2017On.groupby(['Country of asylum (ISO)']).agg({'applied':np.sum})
UNTotalAppsDecs2017On=UNTotalAppsDecs2017On.sort_values(by=['applied'], ascending = False)
UNTotalAppsDecs2017On.head(20)#This is the list of top 20 by volume
UNTotalAppsDecs2017On.reset_index(inplace = True)
# Calculate a new column that formats the applied values as strings with comma-separated thousand values
UNTotalAppsDecs2017On['FormattedApps'] = UNTotalAppsDecs2017On['applied'].apply(lambda x: '{:,.0f}'.format(x))
# Summary Statistic - total volumes of applications received worldwide
TotalApps = UNTotalAppsDecs2017On['applied'].sum()
#%% Create a new dataset for the Top 20 countries only from 2017 onwards
TotalAppsTop20 = UNTotalAppsDecs2017On[(UNTotalAppsDecs2017On['Country of asylum (ISO)']=='USA')|
        (UNTotalAppsDecs2017On['Country of asylum (ISO)']=='DEU')|
        (UNTotalAppsDecs2017On['Country of asylum (ISO)']=='FRA')|
        (UNTotalAppsDecs2017On['Country of asylum (ISO)']=='ESP')|
        (UNTotalAppsDecs2017On['Country of asylum (ISO)']=='PER')|
        (UNTotalAppsDecs2017On['Country of asylum (ISO)']=='MEX')|
        (UNTotalAppsDecs2017On['Country of asylum (ISO)']=='ITA')|
        (UNTotalAppsDecs2017On['Country of asylum (ISO)']=='GRC')|
        (UNTotalAppsDecs2017On['Country of asylum (ISO)']=='CAN')|
        (UNTotalAppsDecs2017On['Country of asylum (ISO)']=='GBR')|
        (UNTotalAppsDecs2017On['Country of asylum (ISO)']=='CRI')|
        (UNTotalAppsDecs2017On['Country of asylum (ISO)']=='TUR')|
        (UNTotalAppsDecs2017On['Country of asylum (ISO)']=='BRA')|
        (UNTotalAppsDecs2017On['Country of asylum (ISO)']=='UGA')|
        (UNTotalAppsDecs2017On['Country of asylum (ISO)']=='AUT')|
        (UNTotalAppsDecs2017On['Country of asylum (ISO)']=='AUS')|
        (UNTotalAppsDecs2017On['Country of asylum (ISO)']=='SWE')|
        (UNTotalAppsDecs2017On['Country of asylum (ISO)']=='EGY')|
        (UNTotalAppsDecs2017On['Country of asylum (ISO)']=='NLD')|
        (UNTotalAppsDecs2017On['Country of asylum (ISO)']=='BEL')]
#Calculate the total number of applications to these countries
TotalAppsTop20Applied = TotalAppsTop20['applied'].sum()
TotalAppsTop20Applied
#Calculate the number of applications to other countries
OtherCountries = TotalApps-TotalAppsTop20Applied
OtherCountries
#%%Pie chart of the proportion asylum applications received between the Top 20 and all other countries
# Create the labels for the pie chart
Countries = ['Top 20 Countries', 'All Other Countries']
# Set the data to be used
data = [TotalAppsTop20Applied, OtherCountries]
# Choose the colours of each segment
colors = ('#002664', '#FC9D9A')
# And plot
fig = plt.figure(figsize = (10,15))
plt.pie(data, labels=Countries,
        autopct=lambda pct: func(pct, data),
        startangle = 165,
        textprops=dict(color='#FFFFFF', fontsize = 24),
        colors = colors,
        wedgeprops = {"edgecolor" : "w", 
                      'linewidth': 2})
# Add title, legend
plt.title('\nProportion of Asylum Applications Received: \n\nTop 20 Countries and All Other Countries, 2017 to June 2023', fontsize = 20, color = '#000000', pad = 20)
plt.legend(loc = 'lower left', fontsize = 14)
# And save the figure as a PNG in your working directory
plt.savefig("AppVolumesPieChart.png")
#%%Plot the application volumes from January 2017 to June 2023 in a line chart
# Create the data for the x-axis
countries = UNTotalAppsDecs2017On['Country of asylum (ISO)'].head(20)
# Set the integer position of each point on the x-axis
pos = np.arange(len(countries))
# Create the data for the y-axis
applications=UNTotalAppsDecs2017On['applied'].head(20)
#%% Plot a line plot of application volumes between January 2017 and June 2023, for each of the Top 20 countires
fig, ax = plt.subplots(figsize=(50, 20))
plt.plot(applications, '-o', linewidth = 5, color = '#002664')
plt.xticks(pos, countries, size = 20)
plt.yticks(size = 20)
#Format the y-axis so it has thousand-value commas
plt.gca().yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
# Remove axes splines
for s in ['top', 'bottom', 'left', 'right']:
    ax.spines[s].set_visible(False)
# Remove the tick marks (- and | from both axes)
plt.tick_params(
    axis='y',
    which='both',
    left=False,
    right=False)
plt.tick_params(
    axis='x',
    which='both',
    top=False,
    bottom=False)
# Add title and labels
plt.title('Asylum Applications: Top 20 Countries: 2017 to June 2023',color = '#000000',fontsize=24, pad = 20)
plt.xlabel('Country of Asylum (ISO)',color = '#000000', fontsize = 20, labelpad = 30)
plt.ylabel('Applications', color = '#000000',fontsize = 20, labelpad = 30)
# Set the y-ticks to empty
plt.yticks([])
# Add annotations that show the application volumes for each country
for x,y in zip(pos,applications):
    label = "{:,.0f}".format(y)
    if x != pos[9] and y!= applications[9]:
        plt.annotate(label, (x,y), textcoords="offset points", xytext=(0,10), ha='center', size =20, bbox=dict(boxstyle="round,pad=0.3",fc="white", ec="#002664", lw=1))
    if x == pos[9] and y == applications[9]:
        plt.annotate(label, (x,y),textcoords="offset points", xytext=(0,10), ha='center', size =20,color = 'w', bbox=dict(boxstyle="round,pad=0.3",fc="#732282", ec="#732282", lw=2))
# Save the plot as a PNG in your working directory
plt.savefig("Applications2017To23.png", bbox_inches = 'tight')
