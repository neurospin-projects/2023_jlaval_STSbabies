input_folder="/neurospin/dico/data/deep_folding/current/datasets/UkBioBank/crops/2mm"
output_folder="/home_local/jc225751/Runs/70_self-supervised_two-regions/Input/UkBioBank/crops/2mm"

regions="S.Pe.C. OCCIPITAL"

for region in $regions;
do 
    input_region=$input_folder/$region/mask
    output_region=$output_folder/$region/mask
    mkdir -p $output_region
    rsync -aP $input_region/*.csv $output_region/
    rsync -aP $input_region/*.npy $output_region/
    echo "$region:"
    ls $output_region
done