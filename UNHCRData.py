# -*- coding: utf-8 -*-
"""
Created on Tue June 11 2024

@author: Kathryn Hopkins
"""
'''
This code analyses and presents UNHCR asylum seeker data from 2000 through 
the latest year available from the API.
A. Asylum Applications
https://www.unhcr.org/refugee-statistics/download/?url=aj1GG7
B. Asylum Decisions
https://www.unhcr.org/refugee-statistics/download/?url=837ayH
'''
# %% Preprocessing - Import requirements
# %% Import Requirements
import os
from io import BytesIO
from datetime import date
from zipfile import BadZipFile, ZipFile
from datetime import datetime
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from matplotlib import style
import matplotlib.ticker as mtick
from matplotlib.ticker import StrMethodFormatter

mpl.rcParams.update(mpl.rcParamsDefault)
# %% Pre-processing - Set up UNHCR API parameters
# %% Retrieve all available data from 2000 through the latest year returned
# by UNHCR.
API_BASE_URL = "https://api.unhcr.org/population/v1"
YEAR_FROM = 2000
last_calendar_year = date.today().year - 1
REQUEST_TIMEOUT_SECONDS = 120
# The UNHCR footnotes identify only these asylum-country/year observations as
# applications reported in cases rather than persons.  A multiplier may be used
# only after aggregating by country of asylum; UNHCR advises against
# applying it
# to country-of-origin results because average case size varies by origin.
# USA 2025 is retained as an explicit 1.0 multiplier because UNHCR counts one
# person per case for the relevant USCIS data that year.
APPLICATION_CASE_TO_PERSON_MULTIPLIERS = {
	**{("GBR", year): 1.3 for year in range(2016, 2023)},
	("USA", 2016): 1.46,
	("USA", 2018): 1.501,
	("USA", 2019): 1.501,
	("USA", 2020): 1.5,
	("USA", 2025): 1.0,
	("KAZ", 2018): 3.0,
}
# %% Pre-processing - Function to download UNHCR CSV data
# %% Function to download UNHCR CSV data
def download_unhcr_csv(dataset):
	"""Download or load a country-level UNHCR dataset and return its CSV as a
	DataFrame."""
	# Check for local CSV file first (or in cache)
	local_csv = f"{dataset}.csv"
	if os.path.exists(local_csv):
		print(f"Loading '{dataset}' from local file '{local_csv}'...")
		return pd.read_csv(local_csv)

	script_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "."
	script_local_csv = os.path.join(script_dir, f"{dataset}.csv")
	if os.path.exists(script_local_csv):
		print(f"Loading '{dataset}' from local file '{script_local_csv}'...")
		return pd.read_csv(script_local_csv)

	cache_parquet = os.path.join(script_dir, "unhcr_cache", f"{dataset}_from_{YEAR_FROM}.parquet")
	if os.path.exists(cache_parquet):
		print(f"Loading '{dataset}' from local cache '{cache_parquet}'...")
		return pd.read_parquet(cache_parquet)

	print(f"Fetching '{dataset}' from UNHCR API ({API_BASE_URL}/{dataset}/)...")
	try:
		response = requests.get(
			f"{API_BASE_URL}/{dataset}/",
			params={
				"yearFrom": YEAR_FROM,
				"download": "true",
				"coo_all": "true",
				"coa_all": "true",
				"cf_type": "ISO",
			},
			timeout=REQUEST_TIMEOUT_SECONDS,
		)
		response.raise_for_status()

		with ZipFile(BytesIO(response.content)) as archive:
			csv_name = f"{dataset}.csv"
			matched_name = next(
				(f for f in archive.namelist() if f.endswith(csv_name)), None
			)
			if not matched_name:
				raise ValueError(
					f"Expected {csv_name} in the UNHCR download, found "
					f"{archive.namelist()}."
				)
			with archive.open(matched_name) as csv_file:
				df = pd.read_csv(csv_file)
				try:
					df.to_csv(local_csv, index=False)
				except Exception:
					pass
				return df
	except Exception as error:
		raise RuntimeError(
			f"Could not load '{dataset}' from local file '{local_csv}' or live API: {error}"
		) from error
# %% Pre-processing - Formatting functions
# %% Function to calculate percentages for pie charts
def func(pct, allvalues):
	absolute = int(pct / 100. * np.sum(allvalues))
	return "{:.1f}%".format(pct, absolute)
# Function to format application outcome labels
def format_application_outcome_label(
		applications, grant_rate, other_protection_rate, refused_rate,
		otherwise_closed_rate
):
	"""Format an accessible application-volume label with all decision
	rates."""
	def rate_label(rate):
		return f'{rate:.0%}' if pd.notna(rate) else 'n/a'

	return (
		f'{format_volume_label(applications)}\n'
		f'G {rate_label(grant_rate)} | OP {rate_label(other_protection_rate)} '
        f'| '
		f'R {rate_label(refused_rate)
        } | C {rate_label(otherwise_closed_rate)}'
	)
def format_volume_label(value):
	if value >= 1_000_000:
		return f'{value / 1_000_000:.1f}m'
	if value >= 1_000:
		return f'{value / 1_000:.0f}k'
	return f'{value:,.0f}'
# %% Pre-processing - Download UNHCR CSV data
# %% Download applications data from the UNHCR API
UNapps = download_unhcr_csv("asylum-applications")
latest_application_year = int(UNapps['Year'].max())
# %% Pre-processing - Download UNHCR Decisions data
# %% Download decisions data from the UNHCR API
UNdecs = download_unhcr_csv("asylum-decisions")
latest_decision_year = int(UNdecs['Year'].max())
latest_available_year = min(latest_application_year, latest_decision_year)
# %% Pre-processing - ISO Country Code Lookup Table
# %% ISO country-code lookup table
# Uses UNHCR's country names for every asylum-country code in the downloaded
# data.
iso_country_names = (
	UNapps[['Country of asylum (ISO)', 'Country of asylum']]
	.dropna()
	.drop_duplicates(subset='Country of asylum (ISO)')
	.rename(columns={
		'Country of asylum (ISO)': 'ISO country code',
		'Country of asylum': 'Country name',
	})
	.sort_values('ISO country code')
	.reset_index(drop=True)
)
# Perform checks on the data
UNapps.head(10)
UNapps.describe()
UNapps.shape
UNapps.axes
UNapps.info()
UNapps['Country of asylum (ISO)'].value_counts(dropna=False)
UNapps['Country of asylum (ISO)'].unique()
# %% ISO Country Code Lookup Table
# %% Show the ISO country code lookup table
iso_country_names[['ISO country code', 'Country name']]
# %% Pre-Processing - Group Applications and Decisions
# %% Group applications and decisions by year, origin and asylum country.
# Case-to-person conversions are deliberately not applied here: UNHCR permits
# them only when data are summarised by country of asylum, not by origin.
# Group applications
UNapps = UNapps.groupby(['Year', 'Country of origin (ISO)',
                         'Country of asylum (ISO)']).agg({'applied': np.sum})
# Group decisions
UNdecs = UNdecs.groupby(['Year', 'Country of origin (ISO)',
                         'Country of asylum (ISO)']).agg(
	{'Recognized decisions': np.sum,
	 'Complementary protection': np.sum,
	 'Rejected decisions': np.sum,
	 'Otherwise closed': np.sum,
	 'Total decisions': np.sum})
# %% Pre-processing - Calculate Grant Rates
# %% Calculate grant rates using the decision data. This is achieved by
# dividing each type of decision by the total number of decisions made.
# Positive asylum decisions ('Granted')
UNdecs['Granted'] = UNdecs['Recognized decisions'] / UNdecs['Total decisions']
# Humanitarian protection ('Other protection')
UNdecs['Other protection'] = UNdecs['Complementary protection'] / UNdecs[
	'Total decisions']
# Negative asylum decisions ('Refused')
UNdecs['Refused'] = UNdecs['Rejected decisions'] / UNdecs['Total decisions']
# Cases closed without a decision ('Otherwise closed')
UNdecs['Otherwise Closed'] = UNdecs['Otherwise closed'] / UNdecs[
	'Total decisions']
# Check that the percentages sum to 100%
UNdecs['Total%'] = UNdecs.loc[:, ['Granted', 'Other protection', 'Refused',
                                  'Otherwise Closed']].sum(axis=1)
UNdecs['Total%'].sum()
# Some of the rows don't sum to 100% - check these
UNdecsCheckTotal = UNdecs[UNdecs['Total%'] != 1.0]
# 1552 rows don't sum properly, some are due to n/a values across the row,
# the others are
len(UNdecsCheckTotal)
len(UNdecs)
# Drop checking column after checking
UNdecs.drop('Total%', axis=1, inplace=True)
# %% Pre-processing - Join Apps and Decs Datasets together
# %%Join Apps and Decs Datasets together
UNTotalAppsDecs = pd.merge(UNapps, UNdecs, how='left', left_index=True,
                           right_index=True)
UNTotalAppsDecs.head()
# and reset the index
UNTotalAppsDecs.reset_index(inplace=True)
# Reset UNapps index so it can be used later
UNapps.reset_index(inplace=True)
# Reset index for later
UNdecs.reset_index(inplace=True)
# Check the application and decision volumes again
UK = UNTotalAppsDecs.loc[
	(UNTotalAppsDecs['Country of asylum (ISO)'] == 'GBR') & (
				UNTotalAppsDecs['Year'] == latest_available_year)]
UK['applied'].sum()
UK['Total decisions'].sum()
UK = UNTotalAppsDecs.loc[
	(UNTotalAppsDecs['Country of asylum (ISO)'] == 'GBR') & (
				UNTotalAppsDecs['Year'] == latest_available_year - 1)]
# UK['applied'].sum()
# UK['Total decisions'].sum()
# %% Pre-processing - Create Datasets
# %% Create Receiving Country dataset (removes country of origin)
UNTotalAppsDecs = UNTotalAppsDecs.groupby(
	['Year', 'Country of asylum (ISO)']).agg(
	{'applied': np.sum, 'Recognized decisions': np.sum,
	 'Complementary protection': np.sum, 'Rejected decisions': np.sum,
	 'Otherwise closed': np.sum, 'Total decisions': np.sum})
# Preserve the raw UNHCR application figure, then convert only the documented
# case-based observations to estimated persons at country-of-asylum level.
UNTotalAppsDecs['Applications (reported)'] = UNTotalAppsDecs['applied']
application_keys = list(zip(
	UNTotalAppsDecs.index.get_level_values('Country of asylum (ISO)'),
	UNTotalAppsDecs.index.get_level_values('Year'),
))
UNTotalAppsDecs['Application case-to-person multiplier'] = (
	pd.Series(application_keys, index=UNTotalAppsDecs.index)
	.map(APPLICATION_CASE_TO_PERSON_MULTIPLIERS)
	.fillna(1.0)
)
UNTotalAppsDecs['Application reporting unit'] = np.where(
	pd.Series(application_keys, index=UNTotalAppsDecs.index).isin(
		APPLICATION_CASE_TO_PERSON_MULTIPLIERS
	),
	'Estimated persons (UNHCR footnote conversion)',
	'Reported persons (no documented conversion)',
)
UNTotalAppsDecs['applied'] = (
		UNTotalAppsDecs['Applications (reported)']
		* UNTotalAppsDecs['Application case-to-person multiplier']
)
# Create new columns in the Receiving Country dataset
UNTotalAppsDecs['Backlog'] = UNTotalAppsDecs['Total decisions'] - \
                             UNTotalAppsDecs['applied']
UNTotalAppsDecs['FVP'] = UNTotalAppsDecs['Total decisions'] / UNTotalAppsDecs[
	'applied']
UNTotalAppsDecs.reset_index(inplace=True)
# %%% 2017 Onwards - Prepare Datasets
# %% 2017 onwards: prepare the Top 20 application analysis
UNTotalAppsDecs2017On = UNTotalAppsDecs[
	UNTotalAppsDecs['Year'].between(2017, latest_available_year)
]
# Create a list of all countries in the dataset
TotalCountries = UNTotalAppsDecs2017On[
	'Country of asylum (ISO)'].unique().tolist()
# %% 2017 Onwards - Identify Top 20 Receiving Countries by Application Volume
# %% 2017 onwards: identify the Top 20 asylum countries by application volume
UNTotalAppsDecs2017On = UNTotalAppsDecs2017On.groupby(
	['Country of asylum (ISO)']).agg({'applied': np.sum})
UNTotalAppsDecs2017On = UNTotalAppsDecs2017On.sort_values(by=['applied'],
                                                          ascending=False)
UNTotalAppsDecs2017On.head(20)  # This is the list of top 20 by volume
UNTotalAppsDecs2017On.reset_index(inplace=True)
# Calculate a new column that formats the applied values as strings with
# comma-separated thousand values
UNTotalAppsDecs2017On['FormattedApps'] = UNTotalAppsDecs2017On[
	'applied'].apply(lambda x: '{:,.0f}'.format(x))
# Summary Statistic - total volumes of applications received worldwide
TotalApps = UNTotalAppsDecs2017On['applied'].sum()
# %% 2017 Onwards - Prepare Chart Data
# %% 2017 onwards: Summarise applications for the Top 20 and all other
# countries
top_20_countries = UNTotalAppsDecs2017On['Country of asylum (ISO)'].head(20)
TotalAppsTop20 = UNTotalAppsDecs2017On[
	UNTotalAppsDecs2017On['Country of asylum (ISO)'].isin(top_20_countries)
].copy()
# Calculate the total number of applications to these countries
TotalAppsTop20Applied = TotalAppsTop20['applied'].sum()
# Calculate the number of applications to other countries
OtherCountries = TotalApps - TotalAppsTop20Applied
# %% 2017 Onwards - Plots
# %% 2017 Onwards - Plot the Top 20 Receiving Countries' Share of Asylum
# Applications as a Pie Chart
# %% 2017 onwards: plot the Top 20 share of asylum applications
# Create the labels for the pie chart
Countries = ['Top 20 Countries', 'All Other Countries']
# Set the data to be used
data = [TotalAppsTop20Applied, OtherCountries]
# Choose the colours of each segment
colors = ('#002664', '#7A7A7A')
# And plot
fig, ax = plt.subplots(figsize=(10, 15))
wedges, texts, autotexts = ax.pie(
	data,
	labels=Countries,
	autopct=lambda pct: func(pct, data),
	startangle=165,
	textprops=dict(color='#FFFFFF', fontsize=24),
	colors=colors,
	wedgeprops={"edgecolor": "w", 'linewidth': 2},
)
# Add title, legend
ax.set_title(
	f'\nProportion of Asylum Applications Received: \n\nTop 20 Countries and '
    f'All Other Countries, 2017 to {latest_available_year}',
	fontsize=20,
	color='#000000',
	pad=20,
)
ax.legend(wedges, Countries, loc='lower left', fontsize=14)
# And save the figure as a PNG in your working directory
fig.savefig("AppVolumesPieChart.png", bbox_inches='tight', dpi=200)
plt.show()
# %% 2017 Onwards - Plot Top 20 Receiving Country Application Volumes as a
# Bar Chart
# %% 2017 onwards: plot Top 20 application volumes as a bar chart
top_20_chart_data = UNTotalAppsDecs2017On.head(20).sort_values('applied')
bar_colors = [
	'#732282' if country == 'GBR' else '#002664'
	for country in top_20_chart_data['Country of asylum (ISO)']
]

fig, ax = plt.subplots(figsize=(12, 9))
bars = ax.barh(
	top_20_chart_data['Country of asylum (ISO)'],
	top_20_chart_data['applied'],
	color=bar_colors,
)
ax.bar_label(
	bars,
	labels=top_20_chart_data['FormattedApps'],
	padding=4,
	fontsize=10,
)
ax.xaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
ax.set_xlabel('Applications', fontsize=12)
ax.set_ylabel('Country of asylum (ISO)', fontsize=12)
ax.set_title(
	f'Top 20 Countries by Asylum Application Volume, 20'
    f'17–{latest_available_year}',
	fontsize=16,
	pad=16,
)
ax.grid(axis='x', linestyle='--', alpha=0.35)
ax.set_axisbelow(True)
for spine in ('top', 'right', 'left'):
	ax.spines[spine].set_visible(False)

fig.tight_layout()
fig.savefig(
	f'Top20_2017_to_{latest_available_year}_application_volumes.png',
	bbox_inches='tight',
	dpi=200,
)
plt.show()
# %% Last Calendar Year - Prepare Datasets
# %% Last calendar year: prepare worldwide totals
last_calendar_year_data = UNTotalAppsDecs[
	UNTotalAppsDecs['Year'] == last_calendar_year]
# Calculate summary statistics for the last calendar year
last_calendar_year_data['applied'].sum()
last_calendar_year_data['Total decisions'].sum()
world_last_calendar_year_backlog = last_calendar_year_data[
	                                   'Total decisions'].sum() - \
                                   last_calendar_year_data['applied'].sum()
# %% Last Calendar Year - Identify Top 20 Receiving Countries by Application
# Volume
# %% Last calendar year: identify the Top 20 asylum countries by application
# volume
top_20_last_calendar_year_countries = (
	last_calendar_year_data
	.sort_values('applied', ascending=False)['Country of asylum (ISO)']
	.head(20)
)
# %% Last Calendar Year - Prepare Chart Datasets
# %% Last calendar year: create the Top 20 application dataset
top_20_last_calendar_year_apps = last_calendar_year_data[
	last_calendar_year_data['Country of asylum (ISO)'].isin(
		top_20_last_calendar_year_countries
	)
].copy()
top_20_last_calendar_year_apps.sort_values(by=['applied'], ascending=False,
                                           inplace=True)
top_20_last_calendar_year_apps.reset_index(inplace=True)
top_20_last_calendar_year_apps = top_20_last_calendar_year_apps.drop('index',
                                                                     axis=1)
# Calculate a new column that formats the applied values as strings with
# comma-separated thousand values
top_20_last_calendar_year_apps['FormattedApps'] = \
top_20_last_calendar_year_apps['applied'].apply(lambda x: '{:,.0f}'.format(x))
# Calculate summary statistics for the last calendar year's data
total_top_20_last_calendar_year_apps = top_20_last_calendar_year_apps[
	'applied'].sum()
total_top_20_last_calendar_year_decisions = top_20_last_calendar_year_apps[
	'Total decisions'].sum()
top_20_last_calendar_year_shortfall = (total_top_20_last_calendar_year_apps -
                                       total_top_20_last_calendar_year_decisions)
# %% Last Calendar Year - Plot Top 20 Receiving Country Application Volumes
# as a Bar Chart
# %% Last calendar year: plot Top 20 application volumes
# Create the data for the x-axis, and their integer position on the axis
countries = top_20_last_calendar_year_apps['Country of asylum (ISO)']
pos = np.arange(len(countries))
# Create the data for the y-axis
applications = top_20_last_calendar_year_apps['applied']
# Plot a ranked horizontal bar chart so every country and value remains
# legible.
last_calendar_year_chart_data = top_20_last_calendar_year_apps.sort_values(
	'applied')
bar_colors = [
	'#732282' if country_code == 'GBR' else '#002664'
	for country_code in
	last_calendar_year_chart_data['Country of asylum (ISO)']
]

fig, ax = plt.subplots(figsize=(12, 9))
bars = ax.barh(
	last_calendar_year_chart_data['Country of asylum (ISO)'],
	last_calendar_year_chart_data['applied'],
	color=bar_colors,
)
ax.bar_label(
	bars,
	labels=last_calendar_year_chart_data['FormattedApps'],
	padding=4,
	fontsize=10,
)
ax.xaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
ax.set_xlabel('Applications', fontsize=12)
ax.set_ylabel('Country of asylum (ISO)', fontsize=12)
ax.set_title(
	f'Top 20 Countries by Asylum Application Volume, {last_calendar_year}',
	fontsize=16,
	pad=16,
)
ax.grid(axis='x', linestyle='--', alpha=0.35)
ax.set_axisbelow(True)
ax.tick_params(axis='y', length=0)
for spine in ('top', 'right', 'left'):
	ax.spines[spine].set_visible(False)
fig.tight_layout()
fig.savefig(f'Top20Applications{last_calendar_year}.png', bbox_inches='tight',
            dpi=200)
plt.show()
# %% Last Calendar Year - Plot Top 20 Receiving Countries Decision Surplus
# or Shortfall as a Bar Chart
# %% Last calendar year: plot Top 20 decision surplus or shortfall
# Backlog is decisions minus applications: negative values are shortfalls.
backlog_chart_data = (
	top_20_last_calendar_year_apps[
		['Country of asylum (ISO)', 'Backlog']
	]
	.copy()
	.sort_values('Backlog', ascending=True)
)
backlog_chart_data['Backlogformatted'] = backlog_chart_data['Backlog'].map(
	'{:,.0f}'.format)
bar_colors = [
	'#732282' if country_code == 'GBR' else '#002664'
	for country_code in backlog_chart_data['Country of asylum (ISO)']
]

fig, ax = plt.subplots(figsize=(12, 9))
bars = ax.barh(
	backlog_chart_data['Country of asylum (ISO)'],
	backlog_chart_data['Backlog'],
	color=bar_colors,
)
ax.bar_label(
	bars,
	labels=backlog_chart_data['Backlogformatted'],
	padding=4,
	fontsize=10,
	color='#000000',
)
ax.axvline(0, color='#000000', linewidth=0.8)
ax.xaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
ax.margins(x=0.12)
ax.set_xlabel('Decision surplus / shortfall (decisions minus applications)',
              fontsize=12)
ax.set_ylabel('Country of asylum (ISO)', fontsize=12)
ax.set_title(
	f'Asylum Decision Surplus or Shortfall: Top 20 Countries, '
    f'{last_calendar_year}',
	fontsize=16,
	pad=16,
)
ax.grid(axis='x', linestyle='--', alpha=0.35)
ax.set_axisbelow(True)
ax.tick_params(axis='y', length=0)
for spine in ('top', 'right', 'left'):
	ax.spines[spine].set_visible(False)
fig.tight_layout()
fig.savefig(f'Backlog{last_calendar_year}.png', bbox_inches='tight', dpi=200)
plt.show()
# %% Worldwide Analysis 2000 to Last Calendar Year - Prepare Chart Datasets
# %% Worldwide analysis: create annual totals and outcome rates
worldwide_annual_data = (
	UNTotalAppsDecs.loc[
		UNTotalAppsDecs['Year'].between(2000, last_calendar_year)]
	.groupby('Year', as_index=False)[
		[
			'applied',
			'Total decisions',
			'Recognized decisions',
			'Rejected decisions',
			'Complementary protection',
			'Otherwise closed',
		]
	]
	.sum()
)
# Annual shortfall is the difference between new applications and decisions
# completed.
worldwide_annual_data['Shortfall'] = (
		worldwide_annual_data['applied'] - worldwide_annual_data[
	'Total decisions']
)
# Grant and refusal rates are calculated from worldwide decision totals each
# year.
worldwide_annual_data['Grant rate'] = (
	worldwide_annual_data['Recognized decisions']
	.div(worldwide_annual_data['Total decisions'])
	.where(worldwide_annual_data['Total decisions'].ne(0))
)
worldwide_annual_data['Refusal rate'] = (
	worldwide_annual_data['Rejected decisions']
	.div(worldwide_annual_data['Total decisions'])
	.where(worldwide_annual_data['Total decisions'].ne(0))
)
worldwide_annual_data['Other protection rate'] = (
	worldwide_annual_data['Complementary protection']
	.div(worldwide_annual_data['Total decisions'])
	.where(worldwide_annual_data['Total decisions'].ne(0))
)
worldwide_annual_data['Otherwise closed rate'] = (
	worldwide_annual_data['Otherwise closed']
	.div(worldwide_annual_data['Total decisions'])
	.where(worldwide_annual_data['Total decisions'].ne(0))
)
# Face-value productivity: decisions completed for each application received.
worldwide_annual_data['FVP'] = (
	worldwide_annual_data['Total decisions']
	.div(worldwide_annual_data['applied'])
	.where(worldwide_annual_data['applied'].ne(0))
)
worldwide_annual_data['Grant rate %'] = worldwide_annual_data[
	'Grant rate'].map(
	lambda rate: f'{rate:.0%}' if pd.notna(rate) else ''
)
worldwide_annual_data['Refusal rate %'] = worldwide_annual_data[
	'Refusal rate'].map(
	lambda rate: f'{rate:.0%}' if pd.notna(rate) else ''
)
worldwide_annual_data['Other protection rate %'] = worldwide_annual_data[
	'Other protection rate'
].map(lambda rate: f'{rate:.0%}' if pd.notna(rate) else '')
worldwide_annual_data['Otherwise closed rate %'] = worldwide_annual_data[
	'Otherwise closed rate'
].map(lambda rate: f'{rate:.0%}' if pd.notna(rate) else '')
worldwide_annual_data['FVP %'] = worldwide_annual_data['FVP'].map(
	lambda value: f'{value:.0%}' if pd.notna(value) else ''
)
worldwide_annual_data
# %% Worldwide 2000 onwards - Plot Worldwide Applications and Decisions
# %% Worldwide applications and decisions
annual_bar_positions = np.arange(len(worldwide_annual_data))
annual_bar_width = 0.42

fig, ax = plt.subplots(figsize=(16, 9))
ax.bar(
	annual_bar_positions - annual_bar_width / 2,
	worldwide_annual_data['applied'],
	width=annual_bar_width,
	color='#002664',
	label='Applications',
)
ax.bar(
	annual_bar_positions + annual_bar_width / 2,
	worldwide_annual_data['Total decisions'],
	width=annual_bar_width,
	color='#732282',
	label='Decisions',
)
ax.set_xticks(annual_bar_positions, worldwide_annual_data['Year'], rotation=45)
ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
ax.set_xlabel('Calendar year', fontsize=12)
ax.set_ylabel('Number of cases', fontsize=12)
ax.set_title(
	f'Worldwide Asylum Applications and Decisions, 2000–{last_calendar_year}',
	fontsize=16,
	pad=16,
)
ax.grid(axis='y', linestyle='--', alpha=0.35)
ax.set_axisbelow(True)
ax.legend(frameon=False)
for spine in ('top', 'right'):
	ax.spines[spine].set_visible(False)
fig.tight_layout()
fig.savefig(
	f'Worldwide_applications_and_decisions_2000_to_{last_calendar_year}.png',
	bbox_inches='tight',
	dpi=200,
)
plt.show()
# %% Worldwide 2000 to Last Calendar Year - Plot Annual Decision-Outcome
# Volumes as a Bar Chart
# %% Plot worldwide annual decision-outcome volumes (not percentage stacked)
worldwide_outcome_columns = [
	'Recognized decisions',
	'Complementary protection',
	'Rejected decisions',
	'Otherwise closed',
]
worldwide_outcome_labels = [
	'Granted',
	'Other protection',
	'Refused',
	'Otherwise closed',
]
# Set colours for the bars
worldwide_outcome_colors = ['#00B050', '#FFD700', '#C53A3A', '#7A7A7A']
fig, ax = plt.subplots(figsize=(16, 9))
bottom = np.zeros(len(worldwide_annual_data))
for column, label, color in zip(
		worldwide_outcome_columns,
		worldwide_outcome_labels,
		worldwide_outcome_colors,
):
	values = worldwide_annual_data[column]
	bars = ax.bar(
		worldwide_annual_data['Year'],
		values,
		bottom=bottom,
		label=label,
		color=color,
		width=0.8,
	)
	ax.bar_label(
		bars,
		labels=[
			format_volume_label(value)
			if value >= total_decisions * 0.04 else ''
			for value, total_decisions in zip(
				values,
				worldwide_annual_data['Total decisions'],
			)
		],
		label_type='center',
		fontsize=8,
		color='#000000' if column in ('Recognized decisions',
		                              'Complementary protection') else
        'white',
	)
	bottom += values.to_numpy()

applications_axis = ax.twinx()
applications_line, = applications_axis.plot(
	worldwide_annual_data['Year'],
	worldwide_annual_data['applied'],
	color='#002664',
	linewidth=2.5,
	linestyle=':',
	marker='o',
	markersize=4,
	label='Applications',
)
applications_axis.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
applications_axis.set_ylabel('Number of applications', fontsize=12)
applications_axis.grid(False)
applications_axis.spines['top'].set_visible(False)

ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
ax.set_xlabel('Calendar year', fontsize=12)
ax.set_ylabel('Number of decisions', fontsize=12)
ax.set_title(
	f'Worldwide Asylum Decisions by Outcome and Applications, 2000–'
    f'{last_calendar_year}',
	fontsize=16,
	pad=16,
)
decision_handles, decision_labels = ax.get_legend_handles_labels()
ax.legend(
	decision_handles + [applications_line],
	decision_labels + ['Applications'],
	title='Measure',
	ncols=3,
	frameon=False,
)
ax.grid(axis='y', linestyle='--', alpha=0.35)
ax.set_axisbelow(True)
ax.tick_params(axis='x', rotation=45)
for spine in ('top', 'right'):
	ax.spines[spine].set_visible(False)
fig.tight_layout()
fig.savefig(
	f'Worldwide_decision_outcomes_2000_to_{last_calendar_year}.png',
	bbox_inches='tight',
	dpi=200,
)
plt.show()
# %% Worldwide 2000 Onwards - Plot Combined Worldwide Decision Outcome Rates
# as a Pie Chart
# %% Plot combined worldwide decision-outcome rates
worldwide_total_decisions = worldwide_annual_data['Total decisions'].sum()
worldwide_total_granted = worldwide_annual_data['Recognized decisions'].sum()
worldwide_total_other_protection = worldwide_annual_data[
	'Complementary protection'].sum()
worldwide_total_refused = worldwide_annual_data['Rejected decisions'].sum()
worldwide_total_otherwise_closed = worldwide_annual_data[
	'Otherwise closed'].sum()

worldwide_outcome_rates = [
	worldwide_total_granted / worldwide_total_decisions,
	worldwide_total_other_protection / worldwide_total_decisions,
	worldwide_total_refused / worldwide_total_decisions,
	worldwide_total_otherwise_closed / worldwide_total_decisions,
]
worldwide_outcome_labels = [
	'Granted',
	'Other protection',
	'Refused',
	'Otherwise closed',
]
worldwide_outcome_colors = ['#00B050', '#FFD700', '#C53A3A', '#7A7A7A']

fig, ax = plt.subplots(figsize=(12, 10))
wedges, _, percentage_labels = ax.pie(
	worldwide_outcome_rates,
	labels=worldwide_outcome_labels,
	autopct='%1.1f%%',
	startangle=90,
	counterclock=False,
	colors=worldwide_outcome_colors,
	wedgeprops={'edgecolor': 'white', 'linewidth': 2},
	textprops={'fontsize': 12},
)
plt.setp(percentage_labels, color='white', fontweight='bold')
ax.set_title(
	f'Worldwide Asylum Decision Outcomes, 2000–{last_calendar_year}',
	fontsize=16,
	pad=20,
)
ax.legend(wedges, worldwide_outcome_labels, loc='lower left', frameon=False)
fig.tight_layout()
fig.savefig(
	f'Worldwide_decision_outcome_rates_2000_to_{last_calendar_year}.png',
	bbox_inches='tight',
	dpi=200,
)
plt.show()
# %% Worldwide 2000 Onwards - Plot Worldwide Decision Outcome Rates Faceted
# by Year
# %% Faceted by year
facet_columns = 5
facet_rows = int(np.ceil(len(worldwide_annual_data) / facet_columns))
fig, axes = plt.subplots(
	facet_rows,
	facet_columns,
	figsize=(facet_columns * 4, facet_rows * 3.8),
)
facet_axes = np.atleast_1d(axes).ravel()

for ax, (_, annual_data) in zip(facet_axes, worldwide_annual_data.iterrows()):
	annual_outcome_rates = [
		annual_data['Recognized decisions'] / annual_data['Total decisions'],
		annual_data['Complementary protection'] / annual_data[
			'Total decisions'],
		annual_data['Rejected decisions'] / annual_data['Total decisions'],
		annual_data['Otherwise closed'] / annual_data['Total decisions'],
	]
	ax.pie(
		annual_outcome_rates,
		autopct=lambda
			percentage: f'{percentage:.0f}%' if percentage >= 4 else '',
		startangle=90,
		counterclock=False,
		colors=worldwide_outcome_colors,
		wedgeprops={'edgecolor': 'white', 'linewidth': 1},
		textprops={'fontsize': 9},
	)
	ax.set_title(str(int(annual_data['Year'])), fontsize=12, pad=6)

for ax in facet_axes[len(worldwide_annual_data):]:
	ax.set_visible(False)

facet_legend_handles = [
	mpl.patches.Patch(color=color, label=label)
	for label, color in zip(worldwide_outcome_labels,
                            worldwide_outcome_colors)
]
fig.legend(
	handles=facet_legend_handles,
	title='Decision outcome',
	loc='lower center',
	ncols=4,
	frameon=False,
)
fig.suptitle(
	f'Worldwide Asylum Decision Outcomes by Year, 2000–{last_calendar_year}',
	fontsize=18,
	y=0.995,
)
fig.tight_layout(rect=(0, 0.05, 1, 0.97))
fig.savefig(
	f'Worldwide_decision_outcome_rates_by_year_2000_to_'
    f'{last_calendar_year}.png',
	bbox_inches='tight',
	dpi=200,
)

plt.show()
# %% Worldwide 2000 Onwards - Plot Worldwide Decision Outcome Rates as a
# Stacked Bar Chart
# %% Plot worldwide annual decision-outcome rates as a stacked bar chart
worldwide_outcome_rate_columns = [
	'Grant rate',
	'Other protection rate',
	'Refusal rate',
	'Otherwise closed rate',
]
# Set colours for the bars
worldwide_outcome_rate_colors = ['#00B050', '#FFD700', '#C53A3A', '#7A7A7A']
fig, ax = plt.subplots(figsize=(16, 9))
rate_bottom = np.zeros(len(worldwide_annual_data))
for column, label, color in zip(
		worldwide_outcome_rate_columns,
		worldwide_outcome_labels,
		worldwide_outcome_rate_colors,
):
	rates = worldwide_annual_data[column].fillna(0)
	bars = ax.bar(
		worldwide_annual_data['Year'],
		rates,
		bottom=rate_bottom,
		label=label,
		color=color,
		width=0.8,
	)
	ax.bar_label(
		bars,
		labels=[f'{rate:.0%}' if rate >= 0.04 else '' for rate in rates],
		label_type='center',
		fontsize=8,
		color='#000000' if column in ('Grant rate',
		                              'Other protection rate') else 'white',
	)
	rate_bottom += rates.to_numpy()
# Set axes etc.
ax.set_ylim(0, 1)
ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
ax.set_xlabel('Calendar year', fontsize=12)
ax.set_ylabel('Share of total decisions', fontsize=12)
ax.set_title(
	f'Worldwide Asylum Decision-Outcome Rates by Year, 20'
    f'00–{last_calendar_year}',
	fontsize=16,
	pad=48,
)
ax.set_xticks(worldwide_annual_data['Year'])
ax.tick_params(axis='x', rotation=45)
ax.grid(axis='y', linestyle='--', alpha=0.35)
ax.set_axisbelow(True)
ax.legend(
	title='Decision outcome',
	loc='upper center',
	bbox_to_anchor=(0.5, 1.08),
	ncols=4,
	frameon=False,
	fontsize=10,
	title_fontsize=11,
)
for spine in ('top', 'right'):
	ax.spines[spine].set_visible(False)
fig.tight_layout()
fig.savefig(
	f'Worldwide_decision_outcome_rates_bar_chart_2000_'
    f'to_{last_calendar_year}.png',
	bbox_inches='tight',
	dpi=200,
)
plt.show()
# %% Worldwide 2000 Onwards - Plot Worldwide Face-Value Productivity Rates
# %% Now plot FVP
worldwide_fvp_smoothed = worldwide_annual_data['FVP'].rolling(
	window=3,
	center=True,
	min_periods=1,
).mean()

fig, ax = plt.subplots(figsize=(14, 8))
ax.plot(
	worldwide_annual_data['Year'],
	worldwide_fvp_smoothed,
	linewidth=2.5,
	color='#002664',
	label='Worldwide FVP (3-year moving average)',
)
ax.axhline(
	y=1,
	color='#882345',
	linestyle='--',
	linewidth=1.5,
	label='100% FVP',
)
ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
ax.set_xlabel('Calendar year', fontsize=12)
ax.set_ylabel('Face-value productivity', fontsize=12)
ax.set_title(
	f'Worldwide Face-Value Productivity (3-Year Moving Average), '
    f'2000–{last_calendar_year}',
	fontsize=16,
	pad=16,
)
ax.grid(axis='y', linestyle='--', alpha=0.35)
ax.set_axisbelow(True)
ax.legend(frameon=False)
ax.tick_params(axis='x', rotation=45)
for spine in ('top', 'right'):
	ax.spines[spine].set_visible(False)
fig.tight_layout()
fig.savefig(
	f'Worldwide_FVP_2000_to_{last_calendar_year}.png',
	bbox_inches='tight',
	dpi=200,
)
plt.show()
# %% Worldwide 2000 onwards - Plot Worldwide Annual Application Shortfall
# %% Plot worldwide annual application shortfall
shortfall_colors = np.where(
	worldwide_annual_data['Shortfall'] >= 0,
	'#C53A3A',
	'#00B050',
)
fig, ax = plt.subplots(figsize=(16, 9))
ax.bar(
	worldwide_annual_data['Year'],
	worldwide_annual_data['Shortfall'],
	color=shortfall_colors,
	width=0.8,
)
ax.axhline(0, color='#000000', linewidth=0.8)
ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
ax.set_xlabel('Calendar year', fontsize=12)
ax.set_ylabel('Applications minus decisions', fontsize=12)
ax.set_title(
	f'Worldwide Annual Asylum Application Shortfall, 20'
    f'00–{last_calendar_year}',
	fontsize=16,
	pad=16,
)
ax.set_xticks(worldwide_annual_data['Year'])
ax.tick_params(axis='x', rotation=45)
ax.grid(axis='y', linestyle='--', alpha=0.35)
ax.set_axisbelow(True)
ax.legend(
	handles=[
		mpl.patches.Patch(color='#C53A3A',
		                  label='Applications exceed decisions'),
		mpl.patches.Patch(color='#00B050',
		                  label='Decisions exceed applications'),
	],
	frameon=False,
)
for spine in ('top', 'right'):
	ax.spines[spine].set_visible(False)
fig.tight_layout()
fig.savefig(
	f'Worldwide_annual_shortfall_2000_to_{last_calendar_year}.png',
	bbox_inches='tight',
	dpi=200,
)
plt.show()
# %% Worldwide 2000 onwards - Plot Worldwide Annual Application Shortfall as
# a Waterfall Chart
# %% Plot worldwide annual shortfall waterfall
waterfall_opening_shortfall = worldwide_annual_data[
	'Shortfall'].cumsum().shift(fill_value=0)
waterfall_colors = np.where(
	worldwide_annual_data['Shortfall'] >= 0,
	'#C53A3A',
	'#00B050',
)

fig, ax = plt.subplots(figsize=(18, 9))
ax.bar(
	worldwide_annual_data['Year'],
	worldwide_annual_data['Shortfall'],
	bottom=waterfall_opening_shortfall,
	color=waterfall_colors,
	width=0.8,
)
ax.axhline(0, color='#000000', linewidth=0.8)
ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
ax.set_xlabel('Calendar year', fontsize=12)
ax.set_ylabel('Net application shortfall since 2000', fontsize=12)
ax.set_title(
	f'Worldwide Asylum Application Shortfall Waterfall, 20'
    f'00–{last_calendar_year}',
	fontsize=16,
	pad=16,
)
ax.set_xticks(worldwide_annual_data['Year'])
ax.tick_params(axis='x', rotation=45)
ax.grid(axis='y', linestyle='--', alpha=0.35)
ax.set_axisbelow(True)
ax.legend(
	handles=[
		mpl.patches.Patch(color='#C53A3A',
		                  label='Applications exceed decisions'),
		mpl.patches.Patch(color='#00B050',
		                  label='Decisions exceed applications'),
	],
	frameon=False,
)
for spine in ('top', 'right'):
	ax.spines[spine].set_visible(False)
fig.tight_layout()
fig.savefig(
	f'Worldwide_shortfall_waterfall_2000_to_{last_calendar_year}.png',
	bbox_inches='tight',
	dpi=200,
)
plt.show()
# %% Individual Countries Analysis
# %% Individual country analyses: Identify Top 20 Receiving Countries from 2000
# to the last calendar year
# %% Identify the Top 20 asylum countries worldwide by total applications
top_20_worldwide_countries = (
	UNTotalAppsDecs.loc[
		UNTotalAppsDecs['Year'].between(2000, latest_available_year)]
	.groupby('Country of asylum (ISO)', as_index=False)['applied']
	.sum()
	.rename(columns={'applied': 'Total applications'})
	.nlargest(20, 'Total applications')
)
top_20_worldwide_countries
# %% Calculate annual FVP for the top 20 countries worldwide
top_20_worldwide_codes = top_20_worldwide_countries['Country of asylum (ISO)']
top_20_worldwide_fvp = (
	UNTotalAppsDecs.loc[
		UNTotalAppsDecs['Year'].between(2000, latest_available_year)
		& UNTotalAppsDecs['Country of asylum (ISO)'].isin(
			top_20_worldwide_codes)
		]
	.groupby(['Year', 'Country of asylum (ISO)'], as_index=False)[
		['applied', 'Total decisions']
	]
	.sum()
)
top_20_worldwide_fvp['FVP'] = (
	top_20_worldwide_fvp['Total decisions']
	.div(top_20_worldwide_fvp['applied'])
	.where(top_20_worldwide_fvp['applied'].ne(0))
)
top_20_worldwide_fvp['FVP smoothed'] = (
	top_20_worldwide_fvp
	.groupby('Country of asylum (ISO)')['FVP']
	.transform(
		lambda fvp: fvp.rolling(window=3, center=True, min_periods=1).mean())
)
# %% Individual Countries - Plot Annual FVP for each Top 20 Receiving Country
# %% Plot annual FVP for each top-20 country
facet_columns = 5
facet_rows = int(np.ceil(len(top_20_worldwide_countries) / facet_columns))
fig, axes = plt.subplots(
	facet_rows,
	facet_columns,
	figsize=(facet_columns * 4, facet_rows * 3.2),
	sharex=True,
)
facet_axes = np.atleast_1d(axes).ravel()
fvp_year_ticks = np.unique(
	np.append(np.arange(2000, latest_available_year + 1, 5),
	          latest_available_year)
)

for ax, country_code in zip(
		facet_axes,
		top_20_worldwide_countries['Country of asylum (ISO)'],
):
	country_fvp = top_20_worldwide_fvp.loc[
		top_20_worldwide_fvp['Country of asylum (ISO)'] == country_code
		]
	ax.plot(
		country_fvp['Year'],
		country_fvp['FVP smoothed'],
		marker='o',
		markersize=3,
		linewidth=1.8,
		color='#732282' if country_code == 'GBR' else '#002664',
	)
	ax.axhline(y=1, color='#882345', linestyle='--', linewidth=1)
	ax.set_title(country_code, fontsize=12, pad=5)
	ax.grid(axis='y', linestyle='--', alpha=0.3)
	ax.set_axisbelow(True)
	ax.set_xticks(fvp_year_ticks)
	ax.tick_params(axis='x', rotation=45, labelsize=8)
	ax.tick_params(axis='y', labelsize=8)
	ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
	for spine in ('top', 'right'):
		ax.spines[spine].set_visible(False)

for ax in facet_axes[len(top_20_worldwide_countries):]:
	ax.set_visible(False)

fig.supxlabel('Calendar year', fontsize=12)
fig.supylabel('Face-value productivity', fontsize=12)
fig.suptitle(
	f'Face-Value Productivity (3-Year Moving Average): Top 20 Countries, '
    f'2000–{latest_available_year}',
	fontsize=18,
	y=0.995,
)
fig.tight_layout(rect=(0.03, 0.03, 1, 0.96))
fig.savefig(
	f'Top_20_country_FVP_2000_to_{latest_available_year}.png',
	bbox_inches='tight',
	dpi=200,
)
plt.show()
# %% Individual Countries - Plot Annual Applications and Decisions for each
# Top 20 Receiving Country as Bar Charts
# %% Plot annual decision outcomes and applications for each top-20 country
top_20_country_outcome_data = (
	UNTotalAppsDecs.loc[
		UNTotalAppsDecs['Year'].between(2000, last_calendar_year)
		& UNTotalAppsDecs['Country of asylum (ISO)'].isin(
			top_20_worldwide_codes)
		]
	.groupby(['Year', 'Country of asylum (ISO)'], as_index=False)[
		[
			'applied',
			'Recognized decisions',
			'Complementary protection',
			'Rejected decisions',
			'Otherwise closed',
		]
	]
	.sum()
)
for country_code in top_20_worldwide_codes:
	country_outcomes = top_20_country_outcome_data.loc[
		top_20_country_outcome_data['Country of asylum (ISO)'] == country_code
		]
	country_total_decisions = country_outcomes[worldwide_outcome_columns].sum(
		axis=1)

	fig, ax = plt.subplots(figsize=(16, 9))
	bottom = np.zeros(len(country_outcomes))
	for column, label, color in zip(
			worldwide_outcome_columns,
			worldwide_outcome_labels,
			worldwide_outcome_colors,
	):
		values = country_outcomes[column]
		bars = ax.bar(
			country_outcomes['Year'],
			values,
			bottom=bottom,
			label=label,
			color=color,
			width=0.8,
		)
		ax.bar_label(
			bars,
			labels=[
				format_volume_label(value)
				if value >= total_decisions * 0.04 else ''
				for value, total_decisions in
				zip(values, country_total_decisions)
			],
			label_type='center',
			fontsize=8,
			color='#000000' if column in ('Recognized decisions',
			                              'Complementary protection') else
            'white',
		)
		bottom += values.to_numpy()

	applications_axis = ax.twinx()
	applications_line, = applications_axis.plot(
		country_outcomes['Year'],
		country_outcomes['applied'],
		color='#002664',
		linewidth=2.5,
		linestyle=':',
		marker='o',
		markersize=4,
		label='Applications',
	)
	applications_axis.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
	applications_axis.set_ylabel('Number of applications', fontsize=12)
	applications_axis.grid(False)
	applications_axis.spines['top'].set_visible(False)

	ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
	ax.set_xlabel('Calendar year', fontsize=12)
	ax.set_ylabel('Number of decisions', fontsize=12)
	ax.set_title(
		f'Asylum Decisions by Outcome and Applications: {country_code}, '
		f'2000–{last_calendar_year}',
		fontsize=16,
		pad=16,
	)
	ax.set_xticks(country_outcomes['Year'])
	ax.tick_params(axis='x', rotation=45)
	ax.grid(axis='y', linestyle='--', alpha=0.35)
	ax.set_axisbelow(True)
	decision_handles, decision_labels = ax.get_legend_handles_labels()
	ax.legend(
		decision_handles + [applications_line],
		decision_labels + ['Applications'],
		title='Measure',
		ncols=3,
		frameon=False,
	)
	for spine in ('top', 'right'):
		ax.spines[spine].set_visible(False)
	fig.tight_layout()
	fig.savefig(
		f'Top_20_{country_code}_decision_outcomes_2000_to_'
        f'{last_calendar_year}.png',
		bbox_inches='tight',
		dpi=200,
	)
	plt.show()
# %% Individual Countries - Plot Annual Shortfall for each Top 20 Receiving Country
# %% Calculate annual shortfall and backlog for the top 20 countries
top_20_country_shortfall_data = (
	UNTotalAppsDecs.loc[
		UNTotalAppsDecs['Year'].between(2000, last_calendar_year)
		& UNTotalAppsDecs['Country of asylum (ISO)'].isin(
			top_20_worldwide_codes)
		]
	.groupby(['Year', 'Country of asylum (ISO)'], as_index=False)[
		['applied', 'Total decisions']
	]
	.sum()
	.sort_values(['Country of asylum (ISO)', 'Year'])
)
top_20_country_shortfall_data['Shortfall'] = (
		top_20_country_shortfall_data['applied']
		- top_20_country_shortfall_data['Total decisions']
)
# This is a lower bound: cases before 2000 are unavailable, and a backlog
# cannot be negative.
minimum_backlog_last_calendar_year = (
	top_20_country_shortfall_data
	.groupby('Country of asylum (ISO)', as_index=False)[
		['applied', 'Total decisions']]
	.sum()
	.rename(columns={
		'applied': 'Applications since 2000',
		'Total decisions': 'Decisions since 2000',
	})
)
minimum_backlog_last_calendar_year['Net shortfall since 2000'] = (
		minimum_backlog_last_calendar_year['Applications since 2000']
		- minimum_backlog_last_calendar_year['Decisions since 2000']
)
minimum_backlog_last_calendar_year['Minimum backlog at last calendar year'] = (
	minimum_backlog_last_calendar_year['Net shortfall since 2000'].clip(
		lower=0)
)
minimum_backlog_last_calendar_year = (
    minimum_backlog_last_calendar_year.sort_values(
	'Minimum backlog at last calendar year', ascending=False
))
# %% Individual Countries - Plot Minimum Backlog at the End of the Last Calendar
# Year for each Top 20 Receiving Country
# %% Plot minimum backlog at the end of the last calendar year for the top
# 20 countries
minimum_backlog_chart_data = minimum_backlog_last_calendar_year.sort_values(
	'Minimum backlog at last calendar year'
)
minimum_backlog_colors = [
	'#732282' if country_code == 'GBR' else '#002664'
	for country_code in minimum_backlog_chart_data['Country of asylum (ISO)']
]

fig, ax = plt.subplots(figsize=(12, 9))
bars = ax.barh(
	minimum_backlog_chart_data['Country of asylum (ISO)'],
	minimum_backlog_chart_data['Minimum backlog at last calendar year'],
	color=minimum_backlog_colors,
)
ax.bar_label(
	bars,
	labels=minimum_backlog_chart_data[
		'Minimum backlog at last calendar year'].map(
		'{:,.0f}'.format
	),
	padding=4,
	fontsize=10,
)
ax.xaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
ax.margins(x=0.1)
ax.set_xlabel('Minimum backlog at end of last calendar year', fontsize=12)
ax.set_ylabel('Country of asylum (ISO)', fontsize=12)
ax.set_title(
	f'Minimum Asylum Backlog at End of {last_calendar_year}: Top 20 '
    f'Countries',
	fontsize=16,
	pad=16,
)
ax.grid(axis='x', linestyle='--', alpha=0.35)
ax.set_axisbelow(True)
ax.tick_params(axis='y', length=0)
for spine in ('top', 'right', 'left'):
	ax.spines[spine].set_visible(False)
fig.tight_layout()
fig.savefig(
	f'Top_20_minimum_backlog_2000_to_{last_calendar_year}.png',
	bbox_inches='tight',
	dpi=200,
)
plt.show()
# %% Individual Countries - Plot Annual Shortfall for each Top 20 Receiving Country
# %% Plot annual shortfall bars for the top 20 countries
facet_columns = 5
facet_rows = int(np.ceil(len(top_20_worldwide_countries) / facet_columns))
facet_year_ticks = np.unique(
	np.append(np.arange(2000, last_calendar_year + 1, 5), last_calendar_year)
)
fig, axes = plt.subplots(
	facet_rows, facet_columns, figsize=(facet_columns * 4, facet_rows * 3.2),
	sharex=True
)
facet_axes = np.atleast_1d(axes).ravel()

for ax, country_code in zip(facet_axes, top_20_worldwide_codes):
	country_shortfall = top_20_country_shortfall_data.loc[
		top_20_country_shortfall_data[
			'Country of asylum (ISO)'] == country_code
		]
	colors = np.where(country_shortfall['Shortfall'] >= 0, '#C53A3A',
	                  '#00B050')
	ax.bar(country_shortfall['Year'], country_shortfall['Shortfall'],
	       color=colors, width=0.8)
	ax.axhline(0, color='#000000', linewidth=0.7)
	ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
	ax.set_title(country_code, fontsize=12, pad=5)
	ax.set_xticks(facet_year_ticks)
	ax.tick_params(axis='x', rotation=45, labelsize=8)
	ax.tick_params(axis='y', labelsize=8)
	ax.grid(axis='y', linestyle='--', alpha=0.3)
	ax.set_axisbelow(True)
	for spine in ('top', 'right'):
		ax.spines[spine].set_visible(False)

fig.legend(
	handles=[
		mpl.patches.Patch(color='#C53A3A',
		                  label='Applications exceed decisions'),
		mpl.patches.Patch(color='#00B050',
		                  label='Decisions exceed applications'),
	],
	loc='upper center', bbox_to_anchor=(0.5, 0.965), ncols=2, frameon=False,
)
fig.supxlabel('Calendar year', fontsize=12, y=0.015)
fig.supylabel('Annual shortfall (applications minus decisions)', fontsize=12)
fig.suptitle(
	f'Annual Asylum Application Shortfall: Top 20 Countries, 20'
    f'00–{last_calendar_year}',
	fontsize=18, y=0.995,
)
fig.tight_layout(rect=(0.04, 0.09, 1, 0.91))
fig.savefig(
	f'Top_20_country_annual_shortfalls_2000_to_{last_calendar_year}.png',
	bbox_inches='tight', dpi=200,
)
plt.show()
# %% Individual Countries - Plot Annual Shortfall for each Top 20 Receiving
# Country as Waterfall Charts
# %% Plot annual shortfall waterfalls for the top 20 countries
fig, axes = plt.subplots(
	facet_rows, facet_columns, figsize=(facet_columns * 4, facet_rows * 3.2),
	sharex=True
)
facet_axes = np.atleast_1d(axes).ravel()
for ax, country_code in zip(facet_axes, top_20_worldwide_codes):
	country_shortfall = top_20_country_shortfall_data.loc[
		top_20_country_shortfall_data[
			'Country of asylum (ISO)'] == country_code
		]
	colors = np.where(country_shortfall['Shortfall'] >= 0, '#C53A3A',
	                  '#00B050')
	opening_shortfall = country_shortfall['Shortfall'].cumsum().shift(
		fill_value=0)
	ax.bar(
		country_shortfall['Year'], country_shortfall['Shortfall'],
		bottom=opening_shortfall, color=colors, width=0.8,
	)
	ax.axhline(0, color='#000000', linewidth=0.7)
	ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
	ax.set_title(f'{country_code} — waterfall', fontsize=11, pad=5)
	ax.set_xticks(facet_year_ticks)
	ax.tick_params(axis='x', rotation=45, labelsize=8)
	ax.tick_params(axis='y', labelsize=8)
	ax.grid(axis='y', linestyle='--', alpha=0.3)
	ax.set_axisbelow(True)
	for spine in ('top', 'right'):
		ax.spines[spine].set_visible(False)

fig.legend(
	handles=[
		mpl.patches.Patch(color='#C53A3A',
		                  label='Applications exceed decisions'),
		mpl.patches.Patch(color='#00B050',
		                  label='Decisions exceed applications'),
	],
	loc='upper center', bbox_to_anchor=(0.5, 0.965), ncols=2, frameon=False,
)
fig.supxlabel('Calendar year', fontsize=12, y=0.015)
fig.supylabel('Annual shortfall (applications minus decisions)', fontsize=12)
fig.suptitle(
	f'Asylum Application Shortfall Waterfalls: Top 20 Countries, '
    f'2000–{last_calendar_year}',
	fontsize=18, y=0.995,
)
fig.tight_layout(rect=(0.04, 0.09, 1, 0.91))
fig.savefig(
	f'Top_20_country_shortfall_waterfalls_2000_to_{last_calendar_year}.png',
	bbox_inches='tight', dpi=200,
)
plt.show()
# %% Individual Countries - Plot Applications and Decisions for Rwanda from 2000
# %% Rwanda decision outcomes and applications from 2000
RWA_CODE = 'RWA'
rwanda_outcomes = (
	UNTotalAppsDecs.loc[
		UNTotalAppsDecs['Year'].between(2000, last_calendar_year)
		& (UNTotalAppsDecs['Country of asylum (ISO)'] == RWA_CODE)
		]
	.groupby('Year', as_index=False)[
		[
			'applied',
			'Recognized decisions',
			'Complementary protection',
			'Rejected decisions',
			'Otherwise closed',
		]
	]
	.sum()
)

if rwanda_outcomes.empty:
	raise ValueError(
		f'No asylum application or decision data were returned f'
        f'or {RWA_CODE}.')

rwanda_total_decisions = rwanda_outcomes[worldwide_outcome_columns].sum(axis=1)
fig, ax = plt.subplots(figsize=(16, 9))
bottom = np.zeros(len(rwanda_outcomes))

for column, label, color in zip(
		worldwide_outcome_columns,
		worldwide_outcome_labels,
		worldwide_outcome_colors,
):
	values = rwanda_outcomes[column]
	bars = ax.bar(
		rwanda_outcomes['Year'],
		values,
		bottom=bottom,
		label=label,
		color=color,
		width=0.8,
	)
	ax.bar_label(
		bars,
		labels=[
			format_volume_label(value) if value >= total * 0.04 else ''
			for value, total in zip(values, rwanda_total_decisions)
		],
		label_type='center',
		fontsize=8,
		color='#000000' if column in ('Recognized decisions',
		                              'Complementary protection') else
        'white',
	)
	bottom += values.to_numpy()

applications_axis = ax.twinx()
applications_line, = applications_axis.plot(
	rwanda_outcomes['Year'],
	rwanda_outcomes['applied'],
	color='#002664',
	linewidth=2.5,
	linestyle=':',
	marker='o',
	markersize=4,
	label='Applications',
)
applications_axis.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
applications_axis.set_ylabel('Number of applications', fontsize=12)
applications_axis.grid(False)
applications_axis.spines['top'].set_visible(False)

ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
ax.set_xlabel('Calendar year', fontsize=12)
ax.set_ylabel('Number of decisions', fontsize=12)
ax.set_title(
	f'Asylum Decisions by Outcome and Applications: Rwanda (RWA), '
    f'2000–{last_calendar_year}',
	fontsize=16,
	pad=16,
)
ax.set_xticks(rwanda_outcomes['Year'])
ax.tick_params(axis='x', rotation=45)
ax.grid(axis='y', linestyle='--', alpha=0.35)
ax.set_axisbelow(True)
decision_handles, decision_labels = ax.get_legend_handles_labels()
ax.legend(
	decision_handles + [applications_line],
	decision_labels + ['Applications'],
	title='Measure',
	ncols=3,
	frameon=False,
)
for spine in ('top', 'right'):
	ax.spines[spine].set_visible(False)
fig.tight_layout()
fig.savefig(
	f'RWA_decision_outcomes_2000_to_{last_calendar_year}.png',
	bbox_inches='tight',
	dpi=200,
)
plt.show()
# %% Individual Countries - Applications by Origin for each Top 20 Receiving
# Countries
# %% Applications by origin for the Top 20 asylum countries
# This keeps the UNHCR-reported application values. Case-to-person multipliers
# cannot be applied here because UNHCR says average case size varies by origin.
origin_country_names = iso_country_names.rename(columns={
	'ISO country code': 'Country of origin (ISO)',
	'Country name': 'Country of origin',
})
asylum_country_names = iso_country_names.rename(columns={
	'ISO country code': 'Country of asylum (ISO)',
	'Country name': 'Country of asylum',
})

top_20_destination_origin_applications = (
	UNapps.loc[
		UNapps['Year'].between(2000, last_calendar_year)
		& UNapps['Country of asylum (ISO)'].isin(top_20_worldwide_codes)
		]
	.groupby(
		['Year', 'Country of asylum (ISO)', 'Country of origin (ISO)'],
		as_index=False,
	)['applied']
	.sum()
	.rename(columns={'applied': 'Applications (reported)'})
	.merge(asylum_country_names, on='Country of asylum (ISO)', how='left')
	.merge(origin_country_names, on='Country of origin (ISO)', how='left')
)

# Some UNHCR aggregates or regional codes have no corresponding country name.
top_20_destination_origin_applications['Country of asylum'] = (
	top_20_destination_origin_applications['Country of asylum']
	.fillna(top_20_destination_origin_applications['Country of asylum (ISO)'])
)
top_20_destination_origin_applications['Country of origin'] = (
	top_20_destination_origin_applications['Country of origin']
	.fillna(top_20_destination_origin_applications['Country of origin (ISO)'])
)
top_20_destination_origin_applications = (
	top_20_destination_origin_applications
	.sort_values(
		['Country of asylum', 'Year', 'Applications (reported)'],
		ascending=[True, True, False],
	)
	.reset_index(drop=True)
)
# %% Individual Countries - Create Application and Grant Rates by Origin for
#  each Top 20 Receiving Country
# %% Summarise application volumes and grant rates by origin and destination
# The Top 10 origin countries per destination are selected by application
# volume, then used in both charts below so the rate chart has the same scope.
top_20_destination_origin_decisions = (
	UNdecs.loc[
		UNdecs['Year'].between(2000, last_calendar_year)
		& UNdecs['Country of asylum (ISO)'].isin(top_20_worldwide_codes)
		]
	.groupby(
		['Country of asylum (ISO)', 'Country of origin (ISO)'],
		as_index=False,
	)[
		[
			'Recognized decisions',
			'Complementary protection',
			'Rejected decisions',
			'Otherwise closed',
			'Total decisions',
		]
	]
	.sum()
)
top_20_destination_origin_summary = (
	top_20_destination_origin_applications
	.groupby(
		[
			'Country of asylum (ISO)',
			'Country of asylum',
			'Country of origin (ISO)',
			'Country of origin',
		],
		as_index=False,
	)['Applications (reported)']
	.sum()
	.merge(
		top_20_destination_origin_decisions,
		on=['Country of asylum (ISO)', 'Country of origin (ISO)'],
		how='left',
	)
)
decision_columns = [
	'Recognized decisions',
	'Complementary protection',
	'Rejected decisions',
	'Otherwise closed',
	'Total decisions',
]
top_20_destination_origin_summary[decision_columns] = (
	top_20_destination_origin_summary[decision_columns].fillna(0)
)
top_20_destination_origin_summary['Grant rate'] = np.where(
	top_20_destination_origin_summary['Total decisions'] > 0,
	top_20_destination_origin_summary['Recognized decisions']
	/ top_20_destination_origin_summary['Total decisions'],
	np.nan,
)
for outcome_column, rate_column in {
	'Complementary protection': 'Other protection rate',
	'Rejected decisions': 'Refused rate',
	'Otherwise closed': 'Otherwise closed rate',
}.items():
	top_20_destination_origin_summary[rate_column] = np.where(
		top_20_destination_origin_summary['Total decisions'] > 0,
		top_20_destination_origin_summary[outcome_column]
		/ top_20_destination_origin_summary['Total decisions'],
		np.nan,
	)
top_20_destination_origin_summary['Origin label'] = (
		top_20_destination_origin_summary['Country of origin']
		+ ' (' + top_20_destination_origin_summary[
			'Country of origin (ISO)'] + ')'
)

top_origins_per_destination = (
	top_20_destination_origin_summary
	.sort_values(
		['Country of asylum (ISO)', 'Applications (reported)'],
		ascending=[True, False],
	)
	.groupby('Country of asylum (ISO)', group_keys=False)
	.head(10)
	.copy()
)
# %% Individual Countries - Plot Applications by Origin for each Top 20 Receiving Country
# %% Plot application volumes by origin for each Top 20 asylum country
facet_columns = 4
facet_rows = int(np.ceil(len(top_20_worldwide_codes) / facet_columns))
fig, axes = plt.subplots(
	facet_rows, facet_columns,
	figsize=(facet_columns * 7, facet_rows * 5.5),
)
facet_axes = np.atleast_1d(axes).ravel()

for ax, country_code in zip(facet_axes, top_20_worldwide_codes):
	origin_data = top_origins_per_destination.loc[
		top_origins_per_destination['Country of asylum (ISO)'] == country_code
		].sort_values('Applications (reported)')
	bars = ax.barh(
		origin_data['Origin label'], origin_data['Applications (reported)'],
		color='#002664'
	)
	ax.bar_label(
		bars,
		labels=[
			(
					f'{volume:,.0f}\n'
					+ (f'G {grant_rate:.0%}' if pd.notna(
				grant_rate) else 'G n/a')
					+ ' | '
					+ (
						f'OP {other_protection_rate:.0%}'
						if pd.notna(other_protection_rate) else 'OP n/a'
					)
					+ ' | '
					+ (f'R {refused_rate:.0%}' if pd.notna(
				refused_rate) else 'R n/a')
					+ ' | '
					+ (
						f'C {otherwise_closed_rate:.0%}'
						if pd.notna(otherwise_closed_rate) else 'C n/a'
					)
			)
			for (
				volume, grant_rate, other_protection_rate, refused_rate,
				otherwise_closed_rate
			) in zip(
				origin_data['Applications (reported)'],
				origin_data['Grant rate'],
				origin_data['Other protection rate'],
				origin_data['Refused rate'],
				origin_data['Otherwise closed rate'],
			)
		],
		padding=3,
		fontsize=7,
	)
	ax.margins(x=0.35)
	ax.xaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
	ax.set_title(f'{country_code}: top applicant origins', fontsize=12, pad=5)
	ax.tick_params(axis='y', labelsize=7)
	ax.tick_params(axis='x', labelsize=8)
	ax.grid(axis='x', linestyle='--', alpha=0.3)
	ax.set_axisbelow(True)
	for spine in ('top', 'right', 'left'):
		ax.spines[spine].set_visible(False)

for ax in facet_axes[len(top_20_worldwide_codes):]:
	ax.set_visible(False)

fig.suptitle(
	f'Application Volumes by Country of Origin: Top 20 Asylum Countries, '
    f'2000–{last_calendar_year}',
	fontsize=18, y=0.995,
)
fig.supxlabel(
	'Applications reported to UNHCR. Labels: G = Granted; OP = Other '
    'protection; '
	'R = Refused; C = Otherwise closed.',
	fontsize=10, y=0.015,
)
fig.tight_layout(rect=(0, 0.03, 1, 0.97))
fig.savefig(
	f'Top_20_destination_application_origins_2000_'
    f'to_{last_calendar_year}.png',
	bbox_inches='tight', dpi=200,
)
plt.show()
# %% Individual Countries - Plot Grant Rates by Origin for each Top 20 Receiving Country
# %% Plot grant rates by origin for each Top 20 asylum country
fig, axes = plt.subplots(
	facet_rows, facet_columns,
	figsize=(facet_columns * 7, facet_rows * 5.5),
	sharex=True,
)
facet_axes = np.atleast_1d(axes).ravel()

for ax, country_code in zip(facet_axes, top_20_worldwide_codes):
	origin_data = top_origins_per_destination.loc[
		top_origins_per_destination['Country of asylum (ISO)'] == country_code
		].sort_values('Applications (reported)')
	has_decisions = origin_data['Grant rate'].notna()
	bars = ax.barh(
		origin_data['Origin label'],
		origin_data['Grant rate'].fillna(0),
		color=np.where(has_decisions, '#00B050', '#7A7A7A'),
	)
	ax.bar_label(
		bars,
		labels=[
			f'{rate:.0%}' if pd.notna(rate) else 'n/a'
			for rate in origin_data['Grant rate']
		],
		padding=3,
		fontsize=7,
	)
	ax.set_title(f'{country_code}: grant rate by applicant origin',
	             fontsize=12, pad=5)
	ax.tick_params(axis='y', labelsize=7)
	ax.tick_params(axis='x', labelsize=8)
	ax.grid(axis='x', linestyle='--', alpha=0.3)
	ax.set_axisbelow(True)
	for spine in ('top', 'right', 'left'):
		ax.spines[spine].set_visible(False)

for ax in facet_axes[len(top_20_worldwide_codes):]:
	ax.set_visible(False)

facet_axes[0].set_xlim(0, 1)
facet_axes[0].xaxis.set_major_formatter(mtick.PercentFormatter(1.0))
fig.suptitle(
	f'Grant Rates by Country of Origin: Top 20 Asylum Countries, '
    f'2000–{last_calendar_year}',
	fontsize=18, y=0.995,
)
fig.supxlabel('Recognized decisions as a share of all decisions', fontsize=12,
              y=0.015)
fig.text(
	0.5, 0.03,
	'Green: grant rate available   •   Grey: no decisions recorded',
	ha='center', fontsize=10,
)
fig.tight_layout(rect=(0, 0.06, 1, 0.97))
fig.savefig(
	f'Top_20_destination_origin_grant_rates_2000_to_{last_calendar_year}.png',
	bbox_inches='tight', dpi=200,
)
plt.show()
# %% Last Calendar Year - Origin and Destination Application Summary
# %% Last-calendar-year origin and destination application summary
last_calendar_year_destination_origin_decisions = (
	UNdecs.loc[
		(UNdecs['Year'] == last_calendar_year)
		& UNdecs['Country of asylum (ISO)'].isin(top_20_worldwide_codes)
		]
	.groupby(
		['Country of asylum (ISO)', 'Country of origin (ISO)'],
		as_index=False,
	)[
		[
			'Recognized decisions',
			'Complementary protection',
			'Rejected decisions',
			'Otherwise closed',
			'Total decisions',
		]
	]
	.sum()
)
last_calendar_year_destination_origin_summary = (
	UNapps.loc[
		(UNapps['Year'] == last_calendar_year)
		& UNapps['Country of asylum (ISO)'].isin(top_20_worldwide_codes)
		]
	.groupby(
		['Country of asylum (ISO)', 'Country of origin (ISO)'],
		as_index=False,
	)['applied']
	.sum()
	.rename(columns={'applied': 'Applications (reported)'})
	.merge(asylum_country_names, on='Country of asylum (ISO)', how='left')
	.merge(origin_country_names, on='Country of origin (ISO)', how='left')
	.merge(
		last_calendar_year_destination_origin_decisions,
		on=['Country of asylum (ISO)', 'Country of origin (ISO)'],
		how='left',
	)
)
last_calendar_year_destination_origin_summary[decision_columns] = (
	last_calendar_year_destination_origin_summary[decision_columns].fillna(0)
)
last_calendar_year_destination_origin_summary['Country of asylum'] = (
	last_calendar_year_destination_origin_summary['Country of asylum']
	.fillna(last_calendar_year_destination_origin_summary[
		        'Country of asylum (ISO)'])
)
last_calendar_year_destination_origin_summary['Country of origin'] = (
	last_calendar_year_destination_origin_summary['Country of origin']
	.fillna(last_calendar_year_destination_origin_summary[
		        'Country of origin (ISO)'])
)
last_calendar_year_destination_origin_summary['Grant rate'] = np.where(
	last_calendar_year_destination_origin_summary['Total decisions'] > 0,
	last_calendar_year_destination_origin_summary['Recognized decisions']
	/ last_calendar_year_destination_origin_summary['Total decisions'],
	np.nan,
)
for outcome_column, rate_column in {
	'Complementary protection': 'Other protection rate',
	'Rejected decisions': 'Refused rate',
	'Otherwise closed': 'Otherwise closed rate',
}.items():
	last_calendar_year_destination_origin_summary[rate_column] = np.where(
		last_calendar_year_destination_origin_summary['Total decisions'] > 0,
		last_calendar_year_destination_origin_summary[outcome_column]
		/ last_calendar_year_destination_origin_summary['Total decisions'],
		np.nan,
	)
last_calendar_year_destination_origin_summary['Origin label'] = (
		last_calendar_year_destination_origin_summary['Country of origin']
		+ ' ('
		+ last_calendar_year_destination_origin_summary[
			'Country of origin (ISO)']
		+ ')'
)
last_calendar_year_top_origins_per_destination = (
	last_calendar_year_destination_origin_summary
	.sort_values(
		['Country of asylum (ISO)', 'Applications (reported)'],
		ascending=[True, False],
	)
	.groupby('Country of asylum (ISO)', group_keys=False)
	.head(10)
	.copy()
)
# %% Individual Countries - Last Calendar Year Origin and Destination
# Application Summary
# %% Plot last-calendar-year application volumes by origin and destination
fig, axes = plt.subplots(
	facet_rows, facet_columns,
	figsize=(facet_columns * 7, facet_rows * 5.5),
)
facet_axes = np.atleast_1d(axes).ravel()

for ax, country_code in zip(facet_axes, top_20_worldwide_codes):
	origin_data = last_calendar_year_top_origins_per_destination.loc[
		last_calendar_year_top_origins_per_destination[
			'Country of asylum (ISO)'] == country_code
		].sort_values('Applications (reported)')
	bars = ax.barh(
		origin_data['Origin label'], origin_data['Applications (reported)'],
		color='#002664'
	)
	ax.bar_label(
		bars,
		labels=[
			(
					f'{volume:,.0f}\n'
					+ (f'G {grant_rate:.0%}' if pd.notna(
				grant_rate) else 'G n/a')
					+ ' | '
					+ (
						f'OP {other_protection_rate:.0%}'
						if pd.notna(other_protection_rate) else 'OP n/a'
					)
					+ ' | '
					+ (f'R {refused_rate:.0%}' if pd.notna(
				refused_rate) else 'R n/a')
					+ ' | '
					+ (
						f'C {otherwise_closed_rate:.0%}'
						if pd.notna(otherwise_closed_rate) else 'C n/a'
					)
			)
			for (
				volume, grant_rate, other_protection_rate, refused_rate,
				otherwise_closed_rate
			) in zip(
				origin_data['Applications (reported)'],
				origin_data['Grant rate'],
				origin_data['Other protection rate'],
				origin_data['Refused rate'],
				origin_data['Otherwise closed rate'],
			)
		],
		padding=3,
		fontsize=7,
	)
	ax.margins(x=0.35)
	ax.xaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
	ax.set_title(f'{country_code}: top applicant origins', fontsize=12, pad=5)
	ax.tick_params(axis='y', labelsize=7)
	ax.tick_params(axis='x', labelsize=8)
	ax.grid(axis='x', linestyle='--', alpha=0.3)
	ax.set_axisbelow(True)
	for spine in ('top', 'right', 'left'):
		ax.spines[spine].set_visible(False)

for ax in facet_axes[len(top_20_worldwide_codes):]:
	ax.set_visible(False)

fig.suptitle(
	f'Application Volumes by Country of Origin: Top 20 Asylum Countrie'
    f's, {last_calendar_year}',
	fontsize=18, y=0.995,
)
fig.supxlabel(
	'Applications reported to UNHCR. Labels: G = Granted; OP = Other '
    'protection; '
	'R = Refused; C = Otherwise closed.',
	fontsize=10, y=0.015,
)
fig.tight_layout(rect=(0, 0.03, 1, 0.97))
fig.savefig(
	f'Top_20_destination_application_origins_{last_calendar_year}.png',
	bbox_inches='tight', dpi=200,
)
plt.show()
# %% Individual Countries - Plot Last Calendar Year Grant Rates by Origin
# for each Top 20 Receiving Country
# %% Plot last-calendar-year grant rates by origin and destination
fig, axes = plt.subplots(
	facet_rows, facet_columns,
	figsize=(facet_columns * 7, facet_rows * 5.5),
	sharex=True,
)
facet_axes = np.atleast_1d(axes).ravel()

for ax, country_code in zip(facet_axes, top_20_worldwide_codes):
	origin_data = last_calendar_year_top_origins_per_destination.loc[
		last_calendar_year_top_origins_per_destination[
			'Country of asylum (ISO)'] == country_code
		].sort_values('Applications (reported)')
	has_decisions = origin_data['Grant rate'].notna()
	bars = ax.barh(
		origin_data['Origin label'],
		origin_data['Grant rate'].fillna(0),
		color=np.where(has_decisions, '#00B050', '#7A7A7A'),
	)
	ax.bar_label(
		bars,
		labels=[
			f'{rate:.0%}' if pd.notna(rate) else 'n/a'
			for rate in origin_data['Grant rate']
		],
		padding=3,
		fontsize=7,
	)
	ax.set_title(f'{country_code}: grant rate by applicant origin',
	             fontsize=12, pad=5)
	ax.tick_params(axis='y', labelsize=7)
	ax.tick_params(axis='x', labelsize=8)
	ax.grid(axis='x', linestyle='--', alpha=0.3)
	ax.set_axisbelow(True)
	for spine in ('top', 'right', 'left'):
		ax.spines[spine].set_visible(False)

for ax in facet_axes[len(top_20_worldwide_codes):]:
	ax.set_visible(False)

facet_axes[0].set_xlim(0, 1)
facet_axes[0].xaxis.set_major_formatter(mtick.PercentFormatter(1.0))
fig.suptitle(
	f'Grant Rates by Country of Origin: Top 20 Asylum Countrie'
    f's, {last_calendar_year}',
	fontsize=18, y=0.995,
)
fig.supxlabel('Recognized decisions as a share of all decisions', fontsize=12,
              y=0.015)
fig.text(
	0.5, 0.03,
	'Green: grant rate available   •   Grey: no decisions recorded',
	ha='center', fontsize=10,
)
fig.tight_layout(rect=(0, 0.06, 1, 0.97))
fig.savefig(
	f'Top_20_destination_origin_grant_rates_{last_calendar_year}.png',
	bbox_inches='tight', dpi=200,
)
plt.show()
# %% Individual Countries - Last Calendar Year Applications and Grant Rates
# %% Compare last-calendar-year applications and grant rates by applicant
# origin
# Application volume and grant rate use separate x-axes because they are
# different measures; each origin has one bar for each measure.
fig, axes = plt.subplots(
	facet_rows, facet_columns,
	figsize=(facet_columns * 8, facet_rows * 5.8),
)
facet_axes = np.atleast_1d(axes).ravel()

for ax, country_code in zip(facet_axes, top_20_worldwide_codes):
	origin_data = last_calendar_year_top_origins_per_destination.loc[
		last_calendar_year_top_origins_per_destination[
			'Country of asylum (ISO)'] == country_code
		].sort_values('Applications (reported)')
	positions = np.arange(len(origin_data))
	application_bars = ax.barh(
		positions - 0.2,
		origin_data['Applications (reported)'],
		height=0.38,
		color='#002664',
		label='Applications',
	)
	ax.bar_label(
		application_bars,
		labels=[f'{value:,.0f}' for value in
		        origin_data['Applications (reported)']],
		padding=3,
		fontsize=6,
		color='#002664',
	)
	ax.margins(x=0.25)
	ax.xaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
	ax.set_yticks(positions, origin_data['Origin label'])
	ax.tick_params(axis='y', labelsize=7)
	ax.tick_params(axis='x', labelsize=8, colors='#002664')
	ax.grid(axis='x', linestyle='--', alpha=0.3)
	ax.set_axisbelow(True)

	rate_axis = ax.twiny()
	has_decisions = origin_data['Grant rate'].notna()
	rate_bars = rate_axis.barh(
		positions + 0.2,
		origin_data['Grant rate'].fillna(0),
		height=0.38,
		color=np.where(has_decisions, '#00B050', '#7A7A7A'),
		label='Grant rate',
	)
	rate_axis.bar_label(
		rate_bars,
		labels=[
			f'{rate:.0%}' if pd.notna(rate) else 'n/a'
			for rate in origin_data['Grant rate']
		],
		padding=3,
		fontsize=6,
		color='#00B050',
	)
	rate_axis.set_xlim(0, 1)
	rate_axis.xaxis.set_major_formatter(mtick.PercentFormatter(1.0))
	rate_axis.tick_params(axis='x', labelsize=8, colors='#00B050')
	rate_axis.spines['top'].set_color('#00B050')

	ax.set_title(f'{country_code}: applications and grant rates', fontsize=12,
	             pad=22)
	for spine in ('top', 'right', 'left'):
		ax.spines[spine].set_visible(False)
	rate_axis.spines['right'].set_visible(False)
	rate_axis.spines['left'].set_visible(False)

for ax in facet_axes[len(top_20_worldwide_codes):]:
	ax.set_visible(False)

fig.legend(
	handles=[
		mpl.patches.Patch(color='#002664', label='Applications (bottom '
                                                 'axis)'),
		mpl.patches.Patch(color='#00B050', label='Grant rate (top axis)'),
		mpl.patches.Patch(color='#7A7A7A', label='Grant rate unavailable'),
	],
	loc='upper center', bbox_to_anchor=(0.5, 0.975), ncols=3, frameon=False,
)
fig.suptitle(
	f'Applications and Grant Rates by Country of Origin: Top 20 Asylum '
    f'Countries, {last_calendar_year}',
	fontsize=18, y=0.995,
)
fig.tight_layout(rect=(0, 0, 1, 0.94))
fig.savefig(
	f'Top_20_destination_applications_and_grant_rat'
    f'es_{last_calendar_year}.png',
	bbox_inches='tight', dpi=200,
)
plt.show()
