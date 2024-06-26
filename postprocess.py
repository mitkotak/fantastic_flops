import argparse
import os
import numpy as np
import pandas as pd

datadir='.'
parser = argparse.ArgumentParser(description='Run a Python script with profiling')
parser.add_argument('csv_file', type=str, default='output', help='Path to the CSV file')
args = parser.parse_args()

files=[x for x in os.listdir(datadir) if x.endswith('.csv') and x.startswith(args.csv_file)]
files.sort()
files=[os.path.join(datadir,file) for file in files]
dfs={}
for file in files:
    tag, ext = os.path.splitext(os.path.basename(file))
    dfs[tag]=pd.DataFrame()
    with open(file,'r') as f:
        cnt=0
        while True:
            ln=f.readline()
            if not ln:
                break
            cnt+=1
            if 'Host Name' in ln:
                break
        df = pd.read_csv(file, skiprows=cnt-1)
        df['Metric Value'] =pd.to_numeric(df['Metric Value'].str.replace(r',','', regex=True))
        dft=df.groupby(['Kernel Name','Metric Name']).sum()
        dfmetric=pd.pivot_table(dft, index='Kernel Name', columns='Metric Name', values='Metric Value')
        dfmetric['Count']=df.groupby(['Kernel Name']).count()['ID'].div(dfmetric.shape[1])

        dfmetric['Time']=dfmetric['sm__cycles_elapsed.avg'] \
                        / (dfmetric['sm__cycles_elapsed.avg.per_second'] /dfmetric['Count'] )

        dfmetric['CC FLOPs']= 2 * dfmetric['sm__sass_thread_inst_executed_op_dfma_pred_on.sum'] \
                                + dfmetric['sm__sass_thread_inst_executed_op_dmul_pred_on.sum'] \
                                + dfmetric['sm__sass_thread_inst_executed_op_dadd_pred_on.sum'] \
                                + 2 * dfmetric['sm__sass_thread_inst_executed_op_ffma_pred_on.sum'] \
                                + dfmetric['sm__sass_thread_inst_executed_op_fmul_pred_on.sum'] \
                                + dfmetric['sm__sass_thread_inst_executed_op_fadd_pred_on.sum'] \
                                + 2 * dfmetric['sm__sass_thread_inst_executed_op_hfma_pred_on.sum'] \
                                + dfmetric['sm__sass_thread_inst_executed_op_hmul_pred_on.sum'] \
                                + dfmetric['sm__sass_thread_inst_executed_op_hadd_pred_on.sum']

        MAGIC_NUMBER = 2048 # Ampere
        # MAGIC_NUMBER = 512 # Turing

        dfmetric['TC FLOPs']= MAGIC_NUMBER * dfmetric['sm__inst_executed_pipe_tensor.sum']
        # Don't know where that 512 is coming from
        dfmetric['all FLOPs']= dfmetric['CC FLOPs'] + dfmetric['TC FLOPs']

        dfmetric['AI HBM'] = dfmetric['all FLOPs'].div(dfmetric['dram__bytes.sum'])
        dfmetric['AI L2'] = dfmetric['all FLOPs'].div(dfmetric['lts__t_bytes.sum'])
        dfmetric['AI L1'] = dfmetric['all FLOPs'].div(dfmetric['l1tex__t_bytes.sum'])
        dfmetric['all GFLOPs'] = dfmetric['all FLOPs'] /1024/1024/1024
        dfmetric['GFLOP/s'] = dfmetric['all GFLOPs']/ dfmetric['Time']
        dfmetric['TC GFLOPs'] = dfmetric['TC FLOPs'] /1024/1024/1024
        dfmetric['TC GFLOP/s'] = dfmetric['TC GFLOPs']/ dfmetric['Time']
        #dfmetric.to_csv('pd_'+tag+'.csv')
        dfs[tag]=dfmetric

print("Measured Time:", sum(dfmetric['Time'].to_list()))
print("Measured GFLOPs:", sum(dfmetric['all GFLOPs'].to_list()))
print("Measured GFLOP/s:", sum(dfmetric['GFLOP/s'].tolist()))
print("Measured TC GFLOP/s:", sum(dfmetric['TC GFLOP/s'].to_list()))
print("Measured TC GFLOPs:", sum(dfmetric['TC GFLOPs'].to_list()))
print("Measured DRAM GB:", dfmetric['dram__bytes.sum'] /1024/1024/1024)
print("Measured L1 GB:", dfmetric['lts__t_bytes.sum'] /1024/1024/1024)
print("Measured L2 GB:", dfmetric['l1tex__t_bytes.sum'] /1024/1024/1024)
