"""Export the actual stopped map for the C++ return-planning regression."""
import argparse
from pathlib import Path
import numpy as np
from scipy.ndimage import distance_transform_edt


def main():
    ap=argparse.ArgumentParser();ap.add_argument('snapshot',type=Path);ap.add_argument('output',type=Path);args=ap.parse_args()
    with np.load(args.snapshot,allow_pickle=False) as data:
        resolution=data['history_geometry'][2]
        observed=data['history_input_valid']>=.5
        physical=(distance_transform_edt(~observed)*resolution<=.25)&~(data['history_rejected']>=.5)
        physical=physical[25:-25,25:-25]
        field=np.stack([data[f'ht_ht_dir_{k}'] for k in range(8)]+[data['ht_ht_valid'],physical],axis=-1)
        # Invalid neural cells have no probability; 0.8 is only a serialization
        # placeholder there. ht_valid remains zero, in both old and new maps.
        field=np.nan_to_num(field,nan=.8)
        rows,cols=physical.shape;cx,cy,res=data['ht_geometry'];x,y,yaw=data['robot']
        with args.output.open('w') as out:
            out.write(f'{rows} {cols} {res:.17g} {cx:.17g} {cy:.17g} {x:.17g} {y:.17g} {yaw:.17g}\n')
            np.savetxt(out,field.reshape(-1,10),fmt='%.9g')


if __name__=='__main__':main()
