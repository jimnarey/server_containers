#!/bin/bash

media_dir="/media/$1/"

readarray -t volumes < <(find "$media_dir" -maxdepth 1 -type d)

unset volumes[0]

vols_map=""

for vol in "${volumes[@]}"
do
   vol_name=${vol#"$media_dir"}
   vol_map="-v=$vol:/mnt/$vol_name"
   vols_map="$vols_map ""$vol_map"
done

echo $vols_map