import sys
sys.path.insert(0, '/data/SPHINX/code')
import argparse
import matplotlib.pyplot as plt
import datetime
from importlib import reload
import logging
import os
import contextlib

# Quickly adding the location of fetchsep to the path to do the imports then delete it from the path 
temp = __import__('pipeline_config').CODE_DIR + '/fetchsep'

sys.path.append(temp)
from fetchsep.opsep import opsep as opsep
from fetchsep.opsep import batch_run_opsep as batch
from fetchsep.utils import config as cfg
from fetchsep.json import ccmc_json_handler as ccmc
from fetchsep.json import keys as keys

del temp

global outpath




############## SET DEFAULTS ##################
showplot = False
saveplot = False
detect_prev_event_default = False #Set to true if get FirstStart flag
two_peaks_default = False #Set to true if get ShortEvent flag

gl_outpath = __import__('pipeline_config').CODE_DIR + '/preprocess/SEPMOD' #setting up where I want to put the files
############## END DEFAULTS #################


logger = logging.getLogger('opsep')
outfname = 'preprocess_result_SEPMOD.list'
#batch.run_all_events(sep_filename, outfname, threshold, umasep)


def main(input_list_name, error_checking):
    temp = __import__('pipeline_config').CODE_DIR + '/fetchsep'
    sys.path.append(temp)
    from fetchsep.opsep import opsep as opsep
    del temp
    # suppressing the output of opsep - most of the output we are interested in for this use
    # case is done with the --ErrorCheck flag
    #with contextlib.redirect_stdout(None):
    start_dates, end_dates, experiments, flux_types, flags, \
            model_names, user_files, json_types, options, bgstart,\
            bgend, json_files, issue_times, trigger_arrays, profile_names = make_sepmod_list(input_list_name)


    #Prepare output file listing events and flags
    if error_checking:
        os.makedirs('./output', exist_ok=True)
        fout = open('./output/' + outfname,"w+")
        fout.write('#Original JSON Name,SEP Date,Exception\n')

    outpath = gl_outpath     #setting up where I want to put the files
    #---RUN ALL SEP EVENTS---
    Nsep = len(start_dates)
    combos = {}
#    print('Read in ' + str(Nsep) + ' SEP events.')
    for i in range(Nsep):
        start_date = start_dates[i]
        end_date = end_dates[i]
        experiment = experiments[i]
        flux_type = flux_types[i]
        flag = flags[i]
        model_name = model_names[i]
        user_file = user_files[i]
        json_type = json_types[i]
        option = options[i]
        bgstartdate = bgstart[i]
        bgenddate = bgend[i]
        user_thresholds = '10,10;100,1;30,1;50,1'
        spase_id = ''

        flag = flag.split(';')
        detect_prev_event = detect_prev_event_default
        two_peaks = two_peaks_default
        doBGSub = False
        if "DetectPreviousEvent" in flag:
            detect_prev_event = True
        if "TwoPeak" in flag:
            two_peaks = True
        if "SubtractBG" in flag:
            doBGSub = True

#        print('\n-------RUNNING SEP ' + start_date + '---------')
        #CALCULATE SEP INFO AND OUTPUT RESULTS TO FILE
        try:
            

            boo = json_files[i].rsplit('SEPMOD')
            
            json_year = boo[2].rsplit('.')[1].rsplit('-')[0]
            json_month = boo[2].rsplit('.')[1].rsplit('-')[1]
            full_path = os.path.join(outpath, json_year, json_month)
            os.makedirs(full_path, exist_ok=True)
            # Changing the normal outpath (which is inside fetchsep),
            # to be my chosen directory
            #opsep.outpath = full_path #Set via arguments
            # again suppressing output here
            
            with contextlib.redirect_stdout(None):

                
                sep_date, jsonfname, event_dict_csv, op_outpath, op_plotpath = opsep.run_opsep(
                    start_date, end_date, experiment, json_mode='forecast',
                    flux_type=flux_type, user_name=model_name, user_file=user_file, json_type=json_type,
                    spase_id=spase_id, showplot=showplot, saveplot=saveplot, detect_prev_event=detect_prev_event,
                    doBGSubOPSEP=doBGSub, doBGSubIDSEP=doBGSub,
                    two_peaks=two_peaks, dointerp=False, user_thresholds = user_thresholds,
                    path_to_output=full_path, directory_depth = 0
                )


                """
                sep_year, sep_month, \
                sep_day, jsonfname = opsep.run_all(start_date, end_date,
                    experiment, flux_type, model_name, user_file, json_type,
                    spase_id, showplot, saveplot, detect_prev_event,
                    two_peaks, False, '', option, doBGSub, bgstartdate,
                    bgenddate, nointerp)
                """
                
                #Update SEPMOD json with the realtime info from the jsons
                #prepared by CCMC for the Scoreboard
                injson = ccmc.read_in_json(jsonfname)
                injson['sep_forecast_submission']['issue_time'] = issue_times[i]
                injson['sep_forecast_submission'].update({'triggers':trigger_arrays[i]})
                
                
                processed_json_name = os.path.join(op_outpath, json_files[i].rsplit('/json/')[1].rsplit('.json')[0] + '_preproc.json')
                
            for blocks in injson['sep_forecast_submission']['forecasts']:
                    current_profile = blocks['sep_profile']
                    energy_string = current_profile.rsplit('.')[3]
                    renamed_profile = json_files[i].rsplit('/json/')[1].rsplit('.json')[0] + '.' + energy_string + 'MeV.txt'
                    blocks['sep_profile'] = renamed_profile
                    try:
                        os.replace(os.path.join(op_outpath, current_profile), os.path.join(op_outpath, renamed_profile))
                    except:
                        os.rename(os.path.join(op_outpath, current_profile), os.path.join(op_outpath, renamed_profile))

            ccmc.write_json(injson, processed_json_name)
            os.remove(jsonfname)

            if error_checking:
                
                fout.write(json_files[i] + ',')
            
                fout.write(str(sep_date) + ', ')
                fout.write('Success\n')

            

            plt.close('all')
            opsep = reload(opsep)
            input()
            
            

        except SystemExit as e:
            # this log will include traceback
            logger.exception('opsep failed with exception')
            # this log will just include content in sys.exit
            logger.error(str(e))
            
            fout.write(json_files[i] + ',')
            fout.write(str(start_date) +',' + '\"' + str(e) + '\"' )
            fout.write('\n')
            opsep = reload(opsep)
            
            continue
            
    if error_checking:
        fout.close()

def make_sepmod_list(input_list_name):
    
    
    start_dates = []
    end_dates = []
    experiments = []
    flux_types = []
    flags = []
    model_names = []
    user_files = []
    json_types = []
    options = []
    bgstartdates = []
    bgenddates = []
    json_files = []
    issue_times = []
    trigger_arrays = []
    sep_profiles = []
    experiment = 'user'
    flux_type = 'integral'
    flag = ''
    model_name = 'SEPMOD'
    json_type = 'model'
    option = ''
    bgstartdate = ''
    bgenddate = ''
    # print(os.path.isfile(input_list_name))
    preprocess_list = open(input_list_name)
    for json_file in preprocess_list:
        json_file = json_file.rstrip()
        json_exists = os.path.isfile(json_file)
#        print(json_file, json_exists)
        # print(json_exists)
        #if not json_exists:
        #    logger.info('JSON file not found ' + str(json_file))
        if json_exists and 'SEPMOD' in json_file:
            # print(json_file)
            start_date = ''
            end_date = ''
            issue_time = ''
            triggers = []
            injson = ccmc.read_in_json(json_file)
            
            pred_st = ccmc.return_json_value_by_index(injson, keys.id_prediction_window_start)
            pred_end = ccmc.return_json_value_by_index(injson, keys.id_prediction_window_end)
            issue_time = injson['sep_forecast_submission']['issue_time']
            triggers = injson['sep_forecast_submission']['triggers']
            profiles = [injson['sep_forecast_submission']['forecasts'][0]['sep_profile'], \
                        injson['sep_forecast_submission']['forecasts'][1]['sep_profile']]
            #print(profiles)
        
            
            sepmod_directory = json_file.rsplit('/json')[0] + '/json/data/'
            # print(sepmod_directory)
            for root, dirs, files in os.walk(sepmod_directory):
               #  print(root, dirs, files)
            
                # start_date = ''
                # end_date = ''
                # issue_time = ''
                # triggers = []
                for file in files:
                   #  print(file)
                    if file.endswith("geo_integral_tseries_timestamped"): 
                        sepmod_fname = os.path.join(root, file)
                        user_file = sepmod_fname
                    # print(user_file, '------------------------------')
                    
        
            start_dates.append(str(pred_st))
            end_dates.append(str(pred_end))
            experiments.append(experiment)
            flux_types.append(flux_type)
            flags.append(flag)
            model_names.append(model_name)
            user_files.append(user_file)
            json_types.append(json_type)
            options.append(option)
            bgstartdates.append(bgstartdate)
            bgenddates.append(bgenddate)
            json_files.append(json_file)
            issue_times.append(issue_time)
            trigger_arrays.append(triggers)
            sep_profiles.append(profiles)
            


    
    return start_dates, end_dates, experiments, flux_types, flags,  \
    model_names, user_files, json_types, options, bgstartdates,\
    bgenddates, json_files, issue_times, trigger_arrays, sep_profiles
    


""" 
    Main Code:
    INPUTS:
        List file from FetchCasts that contains the 'old',
        not processed SEPMOD files. This will be read in then
        used to process the files and be output
    OUTPUTS:
        'Preprocessed' SEPMOD json files with correct energy channel
        and threhold pairs, dumped into a different output directory than
        the originals, where the jsons and time profiles are in year/month
        and threhold pairs, dumped into a different output directory than
        the originals, where the jsons and time profiles are in year/month
        subfolders - like the rest of the scoreboard jsons

"""
parser = argparse.ArgumentParser()
parser.add_argument("--InputListFile", type=str, help=( \
        "Name of the list file from FetchCasts that will be read in"
        "Default is tmp.txt."))
parser.add_argument("--ErrorCheck", action="store_true", help=( \
        "Set to True if you want an output file containing the jsons read in and if they were successfully processed"
        "Default is False."))


args = parser.parse_args()
input_list_name = args.InputListFile
error_checking = args.ErrorCheck




# batch.check_list_path()
if input_list_name:
    main(input_list_name, error_checking)
else:
    fcast_list_path = '/home/m_sphinx/data/forecast_lists'
    for _,_,fcast_list in os.walk(fcast_list_path):
        for i in range(len(fcast_list)):
            if 'clean' in fcast_list[i] and 'fcast' in fcast_list[i]:
                current_fcast_list = os.path.join(fcast_list_path, fcast_list[i])
                print(current_fcast_list)
                main(current_fcast_list, error_checking)
