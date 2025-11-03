#!/usr/bin/python3
from prettytable import PrettyTable
import subprocess, sys
import signal
import os
import numpy as np
import pickle
from datetime import datetime

## command to run ##
# Correction du chemin pour Python 3
cmd = "sudo ryu-manager simple_monitor_AK.py"
flows = {}
TIMEOUT = 15*60

class Flow:
    def __init__(self, time_start, datapath, inport, ethsrc, ethdst, outport, packets, bytes):
        self.time_start = time_start
        self.datapath = datapath
        self.inport = inport
        self.ethsrc = ethsrc
        self.ethdst = ethdst
        self.outport = outport
        
        #attributes for forward flow direction
        self.forward_packets = packets
        self.forward_bytes = bytes
        self.forward_delta_packets = 0
        self.forward_delta_bytes = 0
        self.forward_inst_pps = 0.00
        self.forward_avg_pps = 0.00
        self.forward_inst_bps = 0.00
        self.forward_avg_bps = 0.00
        self.forward_status = 'ACTIVE'
        self.forward_last_time = time_start
        
        #attributes for reverse flow direction
        self.reverse_packets = 0
        self.reverse_bytes = 0
        self.reverse_delta_packets = 0
        self.reverse_delta_bytes = 0
        self.reverse_inst_pps = 0.00
        self.reverse_avg_pps = 0.00
        self.reverse_inst_bps = 0.00
        self.reverse_avg_bps = 0.00
        self.reverse_status = 'INACTIVE'
        self.reverse_last_time = time_start
        
    def updateforward(self, packets, bytes, curr_time):
        self.forward_delta_packets = packets - self.forward_packets
        self.forward_packets = packets
        if curr_time != self.time_start: 
            self.forward_avg_pps = packets/float(curr_time-self.time_start)
        if curr_time != self.forward_last_time: 
            self.forward_inst_pps = self.forward_delta_packets/float(curr_time-self.forward_last_time)
        
        self.forward_delta_bytes = bytes - self.forward_bytes
        self.forward_bytes = bytes
        if curr_time != self.time_start: 
            self.forward_avg_bps = bytes/float(curr_time-self.time_start)
        if curr_time != self.forward_last_time: 
            self.forward_inst_bps = self.forward_delta_bytes/float(curr_time-self.forward_last_time)
        self.forward_last_time = curr_time
        
        if (self.forward_delta_bytes==0 or self.forward_delta_packets==0):
            self.forward_status = 'INACTIVE'
        else:
            self.forward_status = 'ACTIVE'

    def updatereverse(self, packets, bytes, curr_time):
        self.reverse_delta_packets = packets - self.reverse_packets
        self.reverse_packets = packets
        if curr_time != self.time_start: 
            self.reverse_avg_pps = packets/float(curr_time-self.time_start)
        if curr_time != self.reverse_last_time: 
            self.reverse_inst_pps = self.reverse_delta_packets/float(curr_time-self.reverse_last_time)
        
        self.reverse_delta_bytes = bytes - self.reverse_bytes
        self.reverse_bytes = bytes
        if curr_time != self.time_start: 
            self.reverse_avg_bps = bytes/float(curr_time-self.time_start)
        if curr_time != self.reverse_last_time: 
            self.reverse_inst_bps = self.reverse_delta_bytes/float(curr_time-self.reverse_last_time)
        self.reverse_last_time = curr_time

        if (self.reverse_delta_bytes==0 or self.reverse_delta_packets==0):
            self.reverse_status = 'INACTIVE'
        else:
            self.reverse_status = 'ACTIVE'

def predict_traffic_type(model, flow, model_type):
    features = np.asarray([
        flow.forward_delta_packets,
        flow.forward_delta_bytes,
        flow.forward_inst_pps,
        flow.forward_avg_pps,
        flow.forward_inst_bps,
        flow.forward_avg_bps,
        flow.reverse_delta_packets,
        flow.reverse_delta_bytes,
        flow.reverse_inst_pps,
        flow.reverse_avg_pps,
        flow.reverse_inst_bps,
        flow.reverse_avg_bps
    ]).reshape(1, -1)
    
    if model_type == 'random_forest':
        label = model.predict(features)
        return label[0]
    elif model_type == 'supervised':
        label = model.predict(features)
        return label[0]
    elif model_type == 'unsupervised':
        label = model.predict(features)
        if label == 0: return 'dns'
        elif label == 1: return 'ping'
        elif label == 2: return 'telnet'
        elif label == 3: return 'voice'

def printclassifier(model, model_type):
    x = PrettyTable()
    x.field_names = ["Flow ID", "Src MAC", "Dest MAC", "Traffic Type", "Forward Status", "Reverse Status"]

    for key, flow in flows.items():
        try:
            traffic_type = predict_traffic_type(model, flow, model_type)
            x.add_row([key, flow.ethsrc, flow.ethdst, traffic_type, 
                      flow.forward_status, flow.reverse_status])
        except Exception as e:
            print(f"Erreur prédiction: {e}")
    
    print(x)
    print(f"Mise à jour à: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def printflows(traffic_type, f):
    for key, flow in flows.items():
        outstring = '\t'.join([
            str(flow.forward_packets),
            str(flow.forward_bytes),
            str(flow.forward_delta_packets),
            str(flow.forward_delta_bytes), 
            str(flow.forward_inst_pps), 
            str(flow.forward_avg_pps),
            str(flow.forward_inst_bps), 
            str(flow.forward_avg_bps), 
            str(flow.reverse_packets),
            str(flow.reverse_bytes),
            str(flow.reverse_delta_packets),
            str(flow.reverse_delta_bytes),
            str(flow.reverse_inst_pps),
            str(flow.reverse_avg_pps),
            str(flow.reverse_inst_bps),
            str(flow.reverse_avg_bps),
            str(traffic_type)
        ])
        f.write(outstring + '\n')
        
def run_ryu(p, traffic_type=None, f=None, model=None, model_type=None):
    time = 0
    while True:
        out = p.stdout.readline()
        if out == b'' and p.poll() is not None:
            break
        if out != b'' and out.startswith(b'data'):
            fields = out.split(b'\t')[1:]
            
            # Correction pour Python 3
            try:
                fields = [f.decode('utf-8').strip() for f in fields]
            except:
                fields = [f.decode('latin-1').strip() for f in fields]
            
            unique_id = hash(''.join([fields[1], fields[3], fields[4]]))
            if unique_id in flows.keys():
                flows[unique_id].updateforward(int(fields[6]), int(fields[7]), int(fields[0]))
            else:
                rev_unique_id = hash(''.join([fields[1], fields[4], fields[3]]))
                if rev_unique_id in flows.keys():
                    flows[rev_unique_id].updatereverse(int(fields[6]), int(fields[7]), int(fields[0]))
                else:
                    flows[unique_id] = Flow(int(fields[0]), fields[1], fields[2], fields[3], 
                                           fields[4], fields[5], int(fields[6]), int(fields[7]))
            
            if model is not None:
                if time % 10 == 0:
                    printclassifier(model, model_type)
            else:
                printflows(traffic_type, f)
        time += 1

def printHelp():
    print("Usage: sudo python3 traffic_classifier.py [subcommand] [options]")
    print("\tTo collect training data: sudo python3 traffic_classifier.py train [voice|dns|ping|telnet]")
    print("\tUsing unsupervised ML: sudo python3 traffic_classifier.py unsupervised")
    print("\tUsing supervised ML: sudo python3 traffic_classifier.py supervised")
    print("\tUsing Random Forest: sudo python3 traffic_classifier.py random_forest")

def alarm_handler(signum, frame):
    print("Finished collecting data.")
    raise Exception()
    
if __name__ == '__main__':
    SUBCOMMANDS = ('train', 'unsupervised', 'supervised', 'random_forest')

    if len(sys.argv) < 2:
        print("ERROR: Incorrect # of args")
        printHelp()
        sys.exit()

    if sys.argv[1] == "train":
        if len(sys.argv) == 3:
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            traffic_type = sys.argv[2]
            f = open(traffic_type + '_training_data.csv', 'w')
            signal.signal(signal.SIGALRM, alarm_handler)
            signal.alarm(TIMEOUT)
            try:
                headers = 'Forward Packets\tForward Bytes\tDelta Forward Packets\tDelta Forward Bytes\tForward Instantaneous Packets per Second\tForward Average Packets per second\tForward Instantaneous Bytes per Second\tForward Average Bytes per second\tReverse Packets\tReverse Bytes\tDelta Reverse Packets\tDelta Reverse Bytes\tDeltaReverse Instantaneous Packets per Second\tReverse Average Packets per second\tReverse Instantaneous Bytes per Second\tReverse Average Bytes per second\tTraffic Type\n'
                f.write(headers)
                run_ryu(p, traffic_type=traffic_type, f=f)
            except Exception:
                print('Exiting')
                os.killpg(os.getpgid(p.pid), signal.SIGTERM)
                f.close()
        else:
            print("ERROR: specify traffic type.")
            printHelp()
    else:
        model = None
        model_type = sys.argv[1]
        
        if model_type == "random_forest":
            try:
                with open('Random_Forest_Model.pkl', 'rb') as infile:
                    model = pickle.load(infile)
                print("Mode: Random Forest")
            except FileNotFoundError:
                print("Modèle Random Forest non trouvé")
                sys.exit(1)
        elif model_type == "supervised":
            try:
                with open('LogisticRegression', 'rb') as infile:
                    model = pickle.load(infile)
                print("Mode: Logistic Regression")
            except FileNotFoundError:
                print("Modèle Logistic Regression non trouvé")
                sys.exit(1)
        elif model_type == "unsupervised":
            try:
                with open('KMeans_Clustering', 'rb') as infile:
                    model = pickle.load(infile)
                print("Mode: K-Means Clustering")
            except FileNotFoundError:
                print("Modèle K-Means non trouvé")
                sys.exit(1)
        
        if model:
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            run_ryu(p, model=model, model_type=model_type)
