library(VariantAnnotation)
library(splitstackshape)


#Read in sample metadata
get_pcawg_metadata <- function(file_location, split_multi_tumors = T){
  sample_meta = read.table(file_location, header=TRUE, sep="\t")
  
  if(split_multi_tumors){
    library(splitstackshape)
    
    #Split samples with multiple tumors into separate rows
    sample_meta = cSplit(sample_meta, "tumor_wgs_aliquot_id", direction="long")
  }
  
  return(sample_meta)
}

#Read SNV samples from a specified directory
read_snv_samples_from_vcf <- function(sample_location_directory, sample_meta){
  
  files = list.files(sample_location_directory, pattern="*.vcf.gz$", full.names=T, recursive=F)
  
  snv_samples = list()
  
  for(cur_file in files){
    #Extract tumor_wgs_aliquot_id from filename
    cur_tumor_uuid = gsub(".*([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}).*", "\\1", x=cur_file)
    snv_samples[cur_tumor_uuid] = readVcf(cur_file, genome="hs37d5")
  }
}

#Save SNV samples in R format to a specified location
save_snv_samples <- function(snv_samples, file_location){
  save(snv_samples, file=file_location)
}

#When deletions are imported they don't seem to have a proper end recorded
set_deletion_range_ends <- function(dels){
  end(ranges(rowRanges(dels))) = info(dels)$END
}

#Read in germline deletions
read_germline_deletions_from_vcf <- function(file_location, range){
  if(!missing(range)){
    tab = TabixFile(file_location)
    dels = readVcf(tab, "hs37d5", param=range)
  }else{
    dels = readVcf(file_location, genome="hs37d5")
  }
  
  set_deletion_range_ends(dels)
  return(dels)
}

#Save deletions in R format to a specified location
save_deletions_to_r_file <- function(deletions, file_location){
  save(deletions, file=file_location)
}
