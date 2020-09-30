from borg import *
import numpy as np
import pandas as pd
import time
from Borg_Config import *
import requests
from Borg_Simulation import *

### Preinformation ###
# Number of Seeds
nSeeds = 26 ## this seed is for the borg algorithm, it will repeat the process n times with different initial values for hyperparameters

#Number of evaluations in thousands
neval = 200

### Determine Seeds already calculated ###
f = open(os.getcwd() + '/sets_'+Scenario+'_'+str(neval)+'k/'+'/nSeeds.txt',"r")
CalcSeeds = int(f.read())
f.close

### Borg Calculations ###

interim =  np.zeros(nSeeds)

for j in range(nSeeds):
    borg = Borg(nvars, nobjs, nconstrs, simulation_module)
    borg.setBounds(*[[-2, 2]]*12,*[[0.0001, 1]]*5,*[[0,1]]*2)   # 19 Parameters
    borg.setEpsilons(*[1.0]*nobjs)



    ####create runtime file#####
    runtime_filename = os.getcwd() + '/sets_'+Scenario+'_'+str(neval)+'k/' + 'runtime_file_seed_' + str(j+1+CalcSeeds) + '.runtime'

    #result = borg.solve({"maxEvaluations": 100})  # maximum evaluation

    ### Instead of using the original result = borg.solve, the following one would return runtime files for you
    ### frequency controls how often you want to generate the runtime file, feel free to adjust it.
    result = borg.solve({"maxEvaluations": neval * 1000, "runtimeformat": 'borg',
                             "frequency": (neval*1000)/10,
                             "runtimefile": runtime_filename})



    f = open(os.getcwd() + '/sets_'+Scenario+'_'+str(neval)+'k/' + \
        str(j+1+CalcSeeds) + '.set','w')

    #f.write('#Borg Optimization Results\n')
    #f.write('#First ' + str(nvars) + ' are the decision variables, ' \
    #    'last ' + str(nobjs) + ' are the objective values\n')

    # Solution by Vivienne
    f.write('#Borg Optimization Results\n')
    f.write('#First ' + str(nvars) + ' are the decision variables, ' \
                                     'last ' + str(nobjs) + ' are the objective values\n')

    for solution in result:
        line = ''
        for i in range(len(solution.getVariables())):
            line = line + (str(solution.getVariables()[i])) + ' '

        for i in range(len(solution.getObjectives())):
            line = line + (str(solution.getObjectives()[i])) + ' '

        f.write(line[0:-1] + '\n')

        f.write("#")
        
    f.close()

    #CSV Solution for plotting
    f = open(os.getcwd() + '/sets_'+Scenario+'_'+str(neval)+'k/'+ \
        str(j+1+CalcSeeds) + '_csv.set','w')
    for i in range(nvars):
        f.write('Parameter ' + str(i + 1) + ',')
    for i in range(nobjs - 1):
        f.write('Obj ' + str(i + 1) + ',')
    f.write('Obj ' + str(nobjs) + '\n')

    for solution in result:
        line = ''
        for i in range(len(solution.getVariables())):
            line = line + (str(solution.getVariables()[i])) + ','

        for i in range(len(solution.getObjectives()) - 1):
            line = line + (str(solution.getObjectives()[i])) + ','

        line = line + (str(solution.getObjectives()[len(solution.getObjectives()) - 1])) + ' '
        f.write(line[0:-1] + '\n')
    f.close()

    #Track timing
    interim[j] = time.time()

    # Wire Pusher
    title = "HICSS Borg"
    message = "Seed "+str(j+1)+" abgeschlossen, Laufzeit: "+str(round(interim[j]-start,2))+" seconds"
    r = requests.get('https://wirepusher.com/send?id=jF78mpkGt&title=%s&message=%s&type=monitoring' % (title, message))

    print(message)
    #print("Heat Pump load", hp_load[0:24])

# Update Calculated Seeds
f = open(os.getcwd() + '/sets_'+Scenario+'_'+str(neval)+'k/' +'/nSeeds.txt',"w+")
new_calculated_Seeds = CalcSeeds + nSeeds
f.write(str(new_calculated_Seeds))
f.close()

end = time.time()
print("Code finished in ",(round(end-start,2))," seconds")

