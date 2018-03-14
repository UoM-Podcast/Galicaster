#!/bin/bash

# Inputs from Workflow property arguments
MediaPackage_ID=$1
OutputFile=$2

Has_presenter=$3
Has_presentation=$4
Has_presentation2=$5

audio_trim_duration=$6 #"240000"
audio_trim_segments=$7 #"0-14000;16000-22000;"

IFS=';' read -r -a segments <<< "$audio_trim_segments"

if [ $Has_presenter == "true" ]; then
  Has_presenter=true
else
  Has_presenter=false
fi

if [ $Has_presentation == "true" ]; then
  Has_presentation=true
else
  Has_presentation=false
fi

if [ $Has_presentation2 == "true" ]; then
  Has_presentation2=true
else
  Has_presentation2=false
fi

#echo "$MediaPackage_ID $OutputFile $Has_presenter $Has_presentation $Has_presentation2"
#>> $OutputFile

randomString() {
  od -vN 16 -An -tx1 /dev/urandom | tr -d " \n"; echo
}

set -- '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' \
	'<smil version="3.0" baseProfile="Language" xmlns="http://www.w3.org/ns/SMIL" xml:id="s-'"$( randomString )"'" xmlns:oc="http://smil.opencastproject.org">' \
	'<head xmlns="http://www.w3.org/1999/xhtml" xml:id="h-'"$( randomString )"'">' \
	   '<meta name="media-package-id" content="%replace_MediaPackage_ID%" xml:id="meta-'"$( randomString )"'"/>' \
	   '<meta name="track-duration" content="%replace_audio_trim_duration%ms" xml:id="meta-'"$( randomString )"'"/>' \
	   '%replace_head%' \
	'</head>' \
	'<body xmlns="http://www.w3.org/1999/xhtml" xml:id="b-'"$( randomString )"'">' \
	   '%replace_body%' \
	'</body>' \
	'</smil>'
TMP_SMIL="$*"

set -- '<paramGroup xml:id="pg-%head_id%">' \
          '<param valuetype="data" name="track-id" value="'"$( randomString )"'" xml:id="param-'"$( randomString )"'"/>' \
          '<param valuetype="data" name="track-src" value="'"$( randomString )"'" xml:id="param-'"$( randomString )"'"/>' \
          '<param valuetype="data" name="track-flavor" value="%head_flavor%" xml:id="param-'"$( randomString )"'"/>' \
       '</paramGroup>'
TMP_SMIL_HEAD="$*"

set -- '<par xml:id="par-'"$( randomString )"'">' \
          '<video clipBegin="%segment_start%ms" clipEnd="%segment_end%ms" src="'"$( randomString )"'" paramGroup="pg-%paramGroup_id%" xml:id="param-'"$( randomString )"'"/>' \
       '</par>'

TMP_SMIL_BODY="$*"

presenter_id=$( randomString )
presentation_id=$( randomString )
presentation2_id=$( randomString )

SMIL_HEAD=""
SMIL_BODY=""

if $Has_presenter; then
  tmp=${TMP_SMIL_HEAD/"%head_id%"/$presenter_id}
  tmp=${tmp/"%head_flavor%"/"presenter/work"}
  SMIL_HEAD+=$tmp
fi

if $Has_presentation; then
  tmp=${TMP_SMIL_HEAD/"%head_id%"/$presentation_id}
  tmp=${tmp/"%head_flavor%"/"presentation/work"}
  SMIL_HEAD+=$tmp
fi

if $Has_presentation2; then
  tmp=${TMP_SMIL_HEAD/"%head_id%"/$presentation2_id}
  tmp=${tmp/"%head_flavor%"/"presentation2/work"}
  SMIL_HEAD+=$tmp
fi


#echo ${#segments[@]}

# get length of an array
tLen=${#segments[@]}
 
# use for loop read all nameservers
for (( i=0; i<${tLen}; i+=2 ));
do
#for element in "${segments[@]}"
#do
    segment_start=${segments[i]}
    segment_end=${segments[i+1]}
    #echo "$segment_start - $segment_end"

    tmp=${TMP_SMIL_BODY/"%segment_start%"/$segment_start}
    tmp=${tmp/"%segment_end%"/$segment_end}

    if $Has_presenter; then
      SMIL_BODY+=${tmp/"%paramGroup_id%"/$presenter_id}
    fi

    if $Has_presentation; then
      SMIL_BODY+=${tmp/"%paramGroup_id%"/$presentation_id}
    fi

    if $Has_presentation2; then
      SMIL_BODY+=${tmp/"%paramGroup_id%"/$presentation2_id}
    fi
done

# Prepare SMIL
SMIL=${TMP_SMIL/"%replace_MediaPackage_ID%"/$MediaPackage_ID}
SMIL=${SMIL/"%replace_audio_trim_duration%"/$audio_trim_duration}

SMIL=${SMIL/"%replace_head%"/$SMIL_HEAD}
SMIL=${SMIL/"%replace_body%"/$SMIL_BODY}

echo $SMIL >> $OutputFile
exit 0
