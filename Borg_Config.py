#from borg import *
import numpy as np
import pandas as pd
import math
import time

### Start time ###
start = time.time()

### Scenario ###
# IMPORTANT! define this to determine the outpput
#Scenario = 'summer'
Scenario = 'inbetween'
#Scenario = 'winter'
print("Scenario: ", Scenario)
### Import Data ###
# Import Consumer data
Consumer= pd.read_csv('~/PycharmProjects/Borg_charm/Weekly_Data/HH_'+Scenario+'.CSV')
#Consumer= Consumer.drop('Unnamed: 22',axis=1)
Data_shape = Consumer.shape

# Import PV generation
PV_output = pd.read_csv('~/PycharmProjects/Borg_charm/Weekly_Data/PV_'+Scenario+'.CSV')
PV_base = PV_output.to_numpy()

### Electricity Sector ###

# Electricity Consumption
El_Consumption = Consumer.drop(['hour','hh1: heat','hh2: heat','hh3: heat','hh4: heat','hh5: heat','hh6: heat','hh7: heat','hh8: heat','hh9: heat','hh10: heat'], axis=1)
El_Aggregate = El_Consumption.sum(axis=1)
El_Aggregate_list = El_Aggregate.tolist()
El_Aggr_all = np.zeros(Data_shape[0])

#PV feedin and grid Consumption
PV_feedin = np.zeros(Data_shape[0])
Grid_El   = np.zeros(Data_shape[0])
#PV size
PV_max_size = 25

#Battery Level
b_level   = np.zeros(Data_shape[0])
b_load    = np.zeros(Data_shape[0])

#Battery data
b_max_size = 30
b_initial = 0
eta_battery = 0.98 # Battery cyclic efficiency

#PVT system
PVT_max_size_el = 25
PVT_max_size_ht = PVT_max_size_el * 4 #Ht Efficiency is 4 times higher then the el efficiency
PVT_eta_el = 0.80 #with respect to PV
PVT_eta_ht = 4 #with rspect to PV

### Heat Sector ###

#Heat Consumption
Heat_Consumption = Consumer.drop(['hour','hh1: el','hh2: el','hh3: el','hh4: el','hh5: el','hh6: el','hh7: el','hh8: el','hh9: el','hh10: el'], axis=1)
Heat_Aggregate = Heat_Consumption.sum(axis=1)
Heat_Aggregate_list = Heat_Aggregate.tolist()

#Heat storage
ht_max_size = 120
ht_initial = 0
eta_heat = 0.996 # storage efficiency
ht_level  = np.zeros(Data_shape[0])
ht_load   = np.zeros(Data_shape[0]) #heat storage load
#Heat Pump
hp_max_capacity = 20
hp_load   = np.zeros(Data_shape[0]) #heat pump load
hp_cop = 3.5 #Coefficient of performance heat pump
#Combined Heat and power plant
CHP_load = np.zeros(Data_shape[0]) #CHP load
CHP_el = np.zeros(Data_shape[0]) #electric generation
CHP_el_usage = np.zeros(Data_shape[0])
CHP_el_ratio = 0.6

#Excess heat released into the environment
excess_heat = np.zeros(Data_shape[0])

### Price Data ###
#Electricity
feedin_el = 0.10
grid_tariff = 0.30

# Heat
CHP_tariff = 0.10
CHP_feedin_el = 0.08

### CO2 Emissions in kg / kWh ###
grid_co2 = 0.401
CHP_co2_heat = 0.207
PV_co2 = 0.050
PVT_co2 = 0.055
### CO2 Emissions in kg per kW, kWh Capacity ###
battery_co2 = 83.5 # per kWh size
hp_co2 = 1060 # kW size
ht_storage_co2 = 12 # per kWh size

### Investment Costs in €/kWp or €/kWh peak | livetime in years###
# Electric Battery
Invest_battery = 1200
Battery_live = 20
Daybase_battery = Invest_battery/Battery_live/365
# Heat Storage
Invest_htstorage = 40
Htstorage_live = 20
Daybase_htstorage = Invest_htstorage/Htstorage_live/365
# Heat Pump
Invest_hp = 1450
Hp_live = 17
Daybase_hp = Invest_hp/Hp_live/365

# CHP
Invest_chp = 1700
Chp_live = 20
Daybase_chp = Invest_chp/Chp_live/365

# Photovoltaik
Invest_PV = 1400
PV_live = 20
Daybase_PV = Invest_PV/PV_live/365

# Photovoltaik/Thermal
Invest_PVT = 1800
PVT_live = 20
Daybase_PVT = Invest_PVT/PVT_live/365

### Borg Parameters ###
nvars = 19
nobjs = 2
nconstrs = 0

#Objectives
objs = [None]*nobjs

#Constraints
constrs = [None]*nconstrs

## RBFs
n_RBFs = 4
RBF_function = np.zeros(n_RBFs)
parameters = np.zeros(nvars)
Cubic_RBF = np.zeros(n_RBFs)

# Start and Length of time series
# change length to Data_shape[0] for whole time series
timeseries_start = 1
timeseries_length = Data_shape[0]-1

### Import time
importtime = time.time()
print("Data Import finished in ",(round(importtime-start,2))," seconds")
