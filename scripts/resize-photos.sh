# script to resize congress photos into the sizes we typically use
# run from a directory with photos named by bioguide id and then sync resulting 3 directories to S3

for SIZE in "40x50" "100x125" "200x250"
    do
    mkdir $SIZE;
    for f in *.jpg
    do
        convert $f -resize $SIZE^ -gravity center -extent $SIZE $SIZE/$f;
    done
done
