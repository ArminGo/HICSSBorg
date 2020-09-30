#from borg import *
import numpy as np
import pandas as pd
import math
import time
from Borg_Config import *

### Function ###

def simulation_module(*vars):
    #### This is how you parse the parameters returned from borg

    for varcount in range(nvars):
        parameters[varcount] = vars[varcount]

    ### SIMULATION BODY
        ##vars are the policy parameters from Borg
        ##objs are cost, emission and the other objectives you derived from the simulation module
        ##constrs are the constraints for objectives, for example, limiting cost < 10k
        # for n_RBFs = 2
    weight = parameters[0:4]
    center = parameters[4:8]
    radii = parameters[8:12]

    #parameters for Application size
    b_size = parameters[12] * b_max_size # Battery Size
    ht_size = parameters[13] * ht_max_size # Heat Storage size
    hp_capacity = parameters[14] * hp_max_capacity # Heat Pump Capacity
    PV_size = parameters[15] * PV_max_size # PV size
    PVT_size_el = parameters[16] * PVT_max_size_el # PVT size ht
    PVT_size_ht = parameters[16] * PVT_max_size_ht #PVt size el

    # Phase Shift
    a1 = parameters[17] * 2 * np.pi
    a2 = parameters[18] * 2 * np.pi
    ## Cyclic representation of time
    y_t = np.cos((2 * np.pi * Consumer['hour']) / 24 - a1)
    x_t = np.sin((2 * np.pi * Consumer['hour']) / 24 - a2)

    #Clear Heat and Electricity demand Lists
    El_Aggr_all = np.zeros(Data_shape[0])
    Heat_Aggr_all = np.zeros(Data_shape[0])
    # Reset Arrays
    PV_feedin = np.zeros(Data_shape[0])
    Grid_El = np.zeros(Data_shape[0])
    El_Aggr_all = np.zeros(Data_shape[0])
    b_level = np.zeros(Data_shape[0])
    b_load = np.zeros(Data_shape[0])
    CHP_load = np.zeros(Data_shape[0])  # CHP load
    CHP_el = np.zeros(Data_shape[0])  # electric generation
    CHP_el_usage = np.zeros(Data_shape[0])
    b_CHP_load = np.zeros(Data_shape[0]) #Battery Load from CHP electricity
    excess_heat = np.zeros(Data_shape[0])
    ht_level = np.zeros(Data_shape[0])
    ht_load = np.zeros(Data_shape[0])  # heat storage load

    # Use initial battery level heat & el
    b_level[0] = b_initial
    ht_level[0] = ht_initial

    for i in range(timeseries_start, timeseries_start + timeseries_length):
        ### Heat ###
        #Reset Heat
        hp_load = np.zeros(Data_shape[0])

        # Cubic RBF - Determine Heat pump load
        Cubic_RBF[0] = weight[0] * (abs((b_level[i - 1]/b_size - center[0]) / radii[0]) + x_t[i] ** 2 + y_t[i] ** 2) ** 3
        Cubic_RBF[1] = weight[1] * (abs((b_level[i - 1]/b_size - center[1]) / radii[1]) + x_t[i] ** 2 + y_t[i] ** 2) ** 3
        Cubic_RBF[2] = weight[2] * (abs((ht_level[i - 1]/ht_size - center[2]) / radii[2]) + x_t[i] ** 2 + y_t[i] ** 2) ** 3
        Cubic_RBF[3] = weight[3] * (abs((ht_level[i - 1]/ht_size - center[3]) / radii[3]) + x_t[i] ** 2 + y_t[i] ** 2) ** 3

        #Compute Heat pump load
        hp_load[i] = sum(Cubic_RBF)
        hp_load[i] = max(0,min(hp_load[i],hp_capacity*hp_cop)) # supress negative heat pump load, limit capacity


        #1.: Use heat pump to satisfy Heat Demand
        Heat_Aggr_all[i] = Heat_Aggregate[i] - hp_load[i] - PV_base[i,2]*(PVT_size_ht)

        if Heat_Aggr_all[i] >= 0: #2.: Covering Heat Demand
            if ht_level[i-1] > 0: #2.1.: unload battery
                ht_load[i] = min(Heat_Aggr_all[i],ht_level[i-1]*eta_heat)
                ht_level[i] = ht_level[i - 1] - ht_load[i]
                Heat_Aggr_all[i] = Heat_Aggr_all[i] - ht_load[i]
            if Heat_Aggr_all[i] > 0: #2.2: use CHP energy
                CHP_load[i] = Heat_Aggr_all[i]
        else: #3: Heat pump generation is greater than heat demand
            #3.1: Load heat storage
            ht_load[i] = max(Heat_Aggr_all[i], ht_level[i - 1]*eta_heat-ht_size)
            ht_level[i] = ht_level[i - 1]*eta_heat - ht_load[i]
            #3.2: Release excess heat into the environment
            excess_heat[i] = Heat_Aggr_all[i]-ht_load[i]

        ### Electricity ####
        # New Demand
        El_Aggr_all[i] = El_Aggregate[i] + hp_load[i]/hp_cop
        #1.: Use PV
        El_Aggr_all[i] = El_Aggr_all[i] - PV_base[i,2]*(PV_size+PVT_size_el)

        CHP_el [i] = CHP_load[i] * CHP_el_ratio

        #2.: Demand is larger then PV and PVT production
        #2.1: Use CHP
        if El_Aggr_all[i] >= 0:  #CHP
            CHP_el_usage[i] = min(CHP_el[i],El_Aggr_all[i])
            CHP_el[i] = CHP_el[i]-CHP_el_usage[i]
            El_Aggr_all[i] = El_Aggr_all[i]-CHP_el_usage[i]


        #2.2: Demand is larger than PVT, PVT and CHP
        if El_Aggr_all[i] > 0: #2.2.1: Unload battery
            b_load[i] = min(b_level[i - 1], El_Aggr_all[i])
            b_level[i] = b_level[i - 1] - b_load[i]
            El_Aggr_all[i] = El_Aggr_all[i] - b_load[i]

            if El_Aggr_all[i] > 0: #2.2.2: Satisfy rest energy from grid
                Grid_El[i] = El_Aggr_all[i]

        #3.: Local Production is higher then demand
        else:
            # Load Battery with CHP el.
            b_CHP_load[i] = min(CHP_el[i]*eta_battery,b_size-b_level[i - 1])
            b_level[i] = b_level[i - 1] +b_CHP_load[i]
            CHP_el[i] = CHP_el[i] - b_CHP_load[i]

            # Use PV / PVT el.
            if b_level[i] - El_Aggr_all[i]*eta_battery <= b_size:
                #3.1: Save Energy in battery
                b_level[i] = b_level[i] - El_Aggr_all[i]
            else:
                #3.2: Feedin excess energy
                PV_feedin[i] = b_level[i] - El_Aggr_all[i] - b_size
                b_level[i] = b_size

    ### Objectives
    ## Obj 0: Minimize Costs
    # Investment Costs:
    CHP_size = max(CHP_load)

    C_Invest = ((Daybase_battery*b_size + Daybase_htstorage*ht_size + Daybase_hp*hp_capacity + Daybase_PV*PV_size + Daybase_PVT*PVT_size_el + Daybase_chp*CHP_size)/24)*(timeseries_length-1)
    # Datasets contain on blank line for battery initialzation, therefore (timeseries_length-1)

    objs[0] = C_Invest + sum(Grid_El[timeseries_start:(timeseries_start+timeseries_length)]) * grid_tariff - sum(PV_feedin[timeseries_start:(timeseries_start+timeseries_length)]) * feedin_el + sum(CHP_load[timeseries_start:(timeseries_start+timeseries_length)]) * CHP_tariff - sum(CHP_el[timeseries_start:(timeseries_start+timeseries_length)]) * CHP_feedin_el

    ## Obj: 1: Minimize Carbon Footprint

    # Co2 Emissons for THS, BTS, HP (per size)
    
    CO2_THS_BTS_HP =((hp_capacity * hp_co2 / Hp_live) + (ht_size * ht_storage_co2 / Htstorage_live) + (b_size * battery_co2 / Battery_live)) * ((timeseries_length-1) / (365*24))

    objs[1] = CO2_THS_BTS_HP + sum(Grid_El[timeseries_start:(timeseries_start+timeseries_length)]) * grid_co2 + sum(CHP_load[timeseries_start:(timeseries_start+timeseries_length)]) * CHP_co2_heat + sum(PV_base[:,2])*(PV_size * PV_co2 + PVT_size_el * PVT_co2)
    # Obj: Maximize local Energy
    #objs[1] = -(sum(PV_gen[timeseries_start:(timeseries_start+timeseries_length),2]) - sum(PV_feedin[timeseries_start:(timeseries_start+timeseries_length)])) / (sum(El_Aggregate_list[timeseries_start:(timeseries_start+timeseries_length)]) + sum(Heat_Aggregate_list[timeseries_start:(timeseries_start+timeseries_length)]))

    ### Constraints
    # Constr 0: Hp load must be positive
    #hp_load_negative = hp_load[hp_load <= 0]
    #constrs[0] = sum(excess_heat)*0.04
    return (objs)

