#!/usr/bin/env python
import sys
import os
import uuid
from time import sleep
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy import or_, and_
import json
import logging
import argparse
import tracker.model.analysis
import tracker.model.analysis_run
import tracker.model.configuration
from tracker.util import connection

def parse_args():
    my_parser = argparse.ArgumentParser()
    
    sub_parsers = my_parser.add_subparsers()
    
    create_configs_parser = sub_parsers.add_parser("create-configs", conflict_handler='resolve')
    create_configs_parser.add_argument("-a", "--analysis_id", help="ID of the analysis to run.", dest="analysis_id", required=True)
    create_configs_parser.add_argument("-n", "--num_runs", help="Number of runs to create configurations for.", dest="num_runs", required=True, type=int)
    create_configs_parser.add_argument("-c", "--config_location", help="Path to a directory where the generated config files will be stored.", dest="config_location", required=True)
    create_configs_parser.set_defaults(func=create_configs_command)
    
    my_args = my_parser.parse_args()
    
    return my_args

def get_available_samples(analysis_id, num_runs):
    
    #PCAWG Samples are in their own database
    Base = automap_base()        
    sample_engine = create_engine('postgresql://pcawg_admin:pcawg@postgresql.service.consul:5432/pcawg_sample_tracking')        
    Base.prepare(sample_engine, reflect=True)        
                
    PCAWGSample = Base.classes.pcawg_samples
    SampleLocation = Base.classes.sample_locations
                
    sample_session = Session(sample_engine)
    
    #Butler run tracking is in its own database
    Analysis = connection.Base.classes.analysis
    AnalysisRun = connection.Base.classes.analysis_run
    Configuration = connection.Base.classes.configuration
    
    run_session = connection.Session()
    
    normal_sample_id = PCAWGSample.normal_wgs_alignment_gnos_id
    normal_sample_location = SampleLocation.normal_sample_location
    tumour_sample_id = PCAWGSample.tumor_wgs_alignment_gnos_id
    tumour_sample_location = SampleLocation.tumor_sample_location
    
    current_runs = run_session.query(Configuration.config[("sample", "donor_index")].astext).\
        join(AnalysisRun, AnalysisRun.config_id == Configuration.config_id).\
        join(Analysis, Analysis.analysis_id == AnalysisRun.analysis_id).\
        filter(and_(Analysis.analysis_id == analysis_id, AnalysisRun.run_status != tracker.model.analysis_run.RUN_STATUS_ERROR)).all()
        
    available_samples = sample_session.query(PCAWGSample.index.label("index"), normal_sample_id.label("normal_sample_id"), normal_sample_location.label("normal_sample_location"), tumour_sample_id.label("tumour_sample_id"), tumour_sample_location.label("tumour_sample_location")).\
        join(SampleLocation, PCAWGSample.index == SampleLocation.donor_index).\
        filter(and_(normal_sample_location != None, tumour_sample_location != None, PCAWGSample.index.notin_(current_runs), PCAWGSample.dcc_project_code.in_(["PRAD-CA", "PRAD-UK", "PRAD-US", "EOPC-DE"]))).\
        limit(num_runs).all()
        
    run_session.close()
    connection.engine.dispose()
    
    sample_session.close()
    sample_engine.dispose()
    
    
    
    return available_samples, len(available_samples)

def write_config_to_file(config, config_location):
    
    run_uuid = str(uuid.uuid4())
    
    my_file = open("{}/{}.json".format(config_location, run_uuid), "w")
    json.dump(config, my_file)
    my_file.close()

def generate_config_objects(available_samples, num_runs, config_location):
    for this_run in range(num_runs):
        normal_sample_id = available_samples[this_run].normal_sample_id.split(",")[0]
        tumour_sample_id = available_samples[this_run].tumour_sample_id.split(",")[0]
        
        this_config_data = {"sample": {
                                "donor_index": available_samples[this_run].index,
                                "normal_sample_id": normal_sample_id,
                                "normal_sample_location": "/pan-prostate/results/sanger_pcawg_alignments_normal/" + normal_sample_id + "/" + normal_sample_id + ".bam",
                                "tumour_sample_id": tumour_sample_id,
                                "tumour_sample_location": "/pan-prostate/results/sanger_pcawg_alignments/" + tumour_sample_id + "/" + tumour_sample_id + ".bam"
                                }
                            }
        
        yield this_config_data
        

def create_configs_command(args):

    analysis_id = args.analysis_id
    num_runs = args.num_runs
    config_location = args.config_location
    
    available_samples, num_available_samples = get_available_samples(analysis_id, num_runs)
    
    if num_available_samples < num_runs:
        print "Only found {} available samples to run. Will create {} run configurations.".format(str(num_available_samples), str(num_available_samples))
        num_runs = num_available_samples
    
    if (not os.path.isdir(config_location)):
        os.makedirs(config_location)
        
    for config in generate_config_objects(available_samples, num_runs, config_location):
        write_config_to_file(config, config_location)
    
if __name__ == '__main__':
    args = parse_args()
    args.func(args)
    

    
