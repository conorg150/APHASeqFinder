#!/usr/bin/env python

'''
APHASeqfinder
version 4.0.2
submitted to github on 23/12/2021
Javier Nunez, AMR Team, Bacteriology (originally from Nicholas Duggett)
Animal and Plant Health Agency
This script applies a series of filters to the seqfinder results
'''


## loading packages
import sys,os
import pandas as pd
import logging
import warnings
pd.set_option('display.max_columns', 100)



## definition of functions        
def gene_code(id_string):
    '''Given an id string, return the gene prefix, defined as the first four characters after the 
    first underscore.'''
    underscore_index = id_string.find('_')
    return id_string[underscore_index+1:underscore_index+5]

def filter_by_gene(dataframe):
    '''Return the input dataframe with a newly added gene column and row entries filtered to the 
    minimum goodSNPs in each gene category'''
    # Add a column to dataframe with the genes in which each SNP was called. Gene names are defined 
    # as the first 4 characters after the first underscore in the 'id' column of each entry
    dataframe['gene'] = [gene_code(gene) for gene in dataframe['id']]
    # Add a column to the dataframe with the name of the strain the genes are from
    dataframe['strain']=file_name.split(os.sep)[-2]
    idlist = dataframe['id']
    amr_class=list()
    for i in idlist:
        amr_class.append(i[:5])
    dataframe['class']=amr_class
    # Create a dataframe of the lowest 'goodSnps' in each gene category
    grouped_df = dataframe.groupby(by="gene")['perc_mapped'].max()

    # Limit the dataframe to the columns 'gene' and 'good'Snps'. Using an unnamed (lambda) function,
    # create a list of 'True' or 'False' for each entry if it hold the minimum goodSNPs for its
    # gene category
    filter_criteria = dataframe[
                                ['gene','perc_mapped']
                                ].apply(lambda x: (x[0],x[1]) in grouped_df.iteritems(), axis=1)

    # Filter the dataframe by the True/False list and return
    return dataframe[filter_criteria]

def drop_non_syn(dataframe, non_syn_filter):
    '''Remove entries from dataframe where the 'gene' is in the list 'non_syn_filter' and there are 0
    non-synonymous SNPS present'''
    # Define a regular expression for the genes in non_syn_filter. Here each gene in the list is
    # separated by the or operator '|', with any character allowed either side. Eg '.*(gyrA|parC).*'
    gene_regex = ".*(" + "|".join(non_syn_filter) + ").*"

    # Ignore the warning printed when using pd.Series.str.contains() below
    warnings.filterwarnings("ignore", 'This pattern has match groups')

    # Search 'gene' column of dataframe for entries matching gene_regex and 0 non-synonymous SNPs
    matching_indices = dataframe.index[
                                       (dataframe['gene'].str.contains(gene_regex)) &
                                       (dataframe['non'] == 0)
                                       ]
    # Return dataframe with entries that matched criteria (matching_indices) removed
    if not matching_indices.empty:
        # Note: The '~' in the dataframe slice is the logical 'NOT' in pandas
        return dataframe[~dataframe.index.isin(matching_indices)]
    else:
        # Return original dataframe if no entries are to be dropped
        return dataframe


######### Starting
######### reading arguments 
if len(sys.argv)>1:
    file_name = sys.argv[1]
    per_ID=float(sys.argv[2])  
    numsnps=float(sys.argv[3])
    efsa_dict=sys.argv[4]
    database_type=sys.argv[5]
    vir_dict=sys.argv[6]
    reference_name=sys.argv[7]
    dis_dict=sys.argv[8]
else:  # just for developing code
    file_name = '/home/nickduggett/seqfinder_testing/amr_test/4850/4850_CompareTo_AMRDatabase_20200729_and_EnteroPLasmids_20190514_short-tetA6.csv'
    per_ID=70
    numsnps=100
    efsa_dict='/home/nickduggett/APHASeqFinder_4.0.1/EFSA_panel/EFSA_antimcriobial_panel_dictionary_191219.csv'
    database_type="AMR"
    vir_dict='/home/nickduggett/APHASeqFinder_4.0.1/references/virulence/vir_dict_2022_06_17.csv'
    reference_name="AMRDatabase_20200729_and_EnteroPLasmids_20190514_short-tetA6"
    dis_dict='/home/nickduggett/APHASeqFinder_4.0.2/references/disinfectant/disinfectant_dictionary_2022_06_23.csv'

# Read input csv file to dataframe
try:
    data_raw=pd.read_csv(file_name)
    data_raw['reference'] = reference_name
except (IOError, IndexError):
    print("Check "+file_name)
    sys.exit()
    
if database_type=="AMR":
    data_raw["EFSA_dict"]=efsa_dict
elif database_type=="VIR":
    data_raw["Vir_dict"]=vir_dict
elif database_type=="DIS":
    data_raw["Dis_dict"]=dis_dict
else:data_raw=data_raw

if database_type=="AMR":
    # This line makes floR circumvent the filtering rules below if floR maps to more than 99%
    floR_rule = data_raw[(data_raw['perc_mapped'] >= 99) & (data_raw['id'] == 'chlor-g1585_floR')]
    gyrA_rule = data_raw[(data_raw['perc_mapped'] >= 98) & (data_raw['good_snps'] <= 100) & (data_raw['id'] == 'quino-g1763_gyrA_ecol_Chr')]
    #logging.info('Analysing results from "{}" '.format(sys.argv[1]))
    
    # Filter dataframe by % real SNPs and goodSNP count
    data_low_snps = data_raw[(data_raw['perc_mapped'] >= per_ID) & (data_raw['good_snps'] <= numsnps)].copy()
    
    # We now drop floR from the dataframe to ensure that it does not occur twice if the %mapped threshold is set below 99
    drop_floR = data_low_snps[(data_low_snps.id != 'chlor-g1585_floR') & (data_low_snps.id != 'quino-g1763_gyrA_ecol_Chr')]
    #drop_gyrA = data_low_snps[data_low_snps.id != 'quino-g1763_gyrA_ecol_Chr']
    # Merge the floR_rule above with the filtering rules set out in data_low_snps
    merge_floR = drop_floR,floR_rule,gyrA_rule
    data_low_snps = pd.concat(merge_floR)
else:
    data_low_snps=data_raw.copy()

###################################
#list_of_genes=['betaL-g0197_ampC_Chr','macro-g1725_mdfA_Chr','quino-g1763_gyrA_ecol_Chr','quino-g1809_parC_ecol_Chr','nitro-g1757_nfsA_Chr','fosfo-g1604_glpT_Chr','fosfo-g1606_ptsI_Chr','fosfo-g1607_uhpA_Chr','colis-g2212_phoP_EC_MG1655_Chr','colis-g2215_acrR_EC_MG1655_Chr']
#normalisation_genes = data_low_snps[data_low_snps.id.isin(list_of_genes)]
#number_of_genes = normalisation_genes.shape[0]
#sum_of_normalisation_genes = normalisation_genes['meanCov'].sum()
#mean_of_normalisation_genes = (sum_of_normalisation_genes / number_of_genes)
#data_low_snps["normCov"]=data_low_snps['meanCov'] / mean_of_normalisation_genes
###################################


# Select dataframe row entries with the lowest number of SNPs for each 'gene' category
data_gene_filtered = filter_by_gene(data_low_snps).copy()
#Create filter rule to group each set of genes by the lowest number of goodsnps
data_gene_filtered_snps=data_gene_filtered.groupby("gene")["good_snps"].min()
filter_criteria_snps = data_gene_filtered[['gene','good_snps']].apply(lambda x: (x[0],x[1]) in data_gene_filtered_snps.iteritems(), axis=1)
#Apply the filtered results to the main dataframe
data_gene_filtered=data_gene_filtered[filter_criteria_snps]


if database_type=="AMR":

    # Create a list of AMR genes to pass to drop_non_syn(). These strings will be searched for
    # in the 'gene' column, and will only be reported if non-synonymous SNPS are present.
    # Note: Each string in the list is searched with a wildcard before and after e.g *gyrA*
    drop_non_syn_0 = ['gyr','par','pmr','P3','P4','P5','sox','folP','bas','pts','Pc_P','Pa_P','omp','nfs','pho','etk','acr','amp','uhp','glp','mdf','mur']
    
    # Remove entries with 0 non-synonymous SNPs for each gene in drop_non_syn_0
    data_output = drop_non_syn(data_gene_filtered, drop_non_syn_0).copy()
    logging.info('Searched for #non == 0 in {}. '.format(drop_non_syn_0) + 'Report will display {} entries.'.format(data_output.shape[0]))
    ###Filter tet34 unless it hits at more than 90% mapped-gaps/real
    tet34_filter = data_output[(data_output['id'] == 'tetra-g1901_tet34') & (data_output['perc_mapped'] >= 90)]
    #drop_tet34 = data_output[(data_output.id != 'tetra-g1901_tet34')]
    ###Filter ampP from data_output if it does not contain snps in position 110 or 120
    ampP_filter = (data_output[data_output['gene'].str.contains("ampP")])
    ampP_snps_stringent = ['110-C-T-','120-']
    ampP_filter_snps = ampP_filter['annotation'].str.contains('|'.join(ampP_snps_stringent))
    df_ampP_filter_snps = ampP_filter[ampP_filter_snps]
    ###Setting up variable to remove ampP, gyrA and parC from original output
    #drop_ampP_gyrA_parC = data_output[(data_output.gene != 'ampP') & (data_output.gene != 'gyrA') & (data_output.gene != 'parC') & (data_output.id != 'tetra-g1901_tet34')& (data_output.gene != 'ant3')]
    drop_ampP_gyrA_parC = data_output[~data_output.id.str.contains("_Chr")&(data_output.id != 'tetra-g1901_tet34')& (data_output.gene != 'ant3')]   
    data_output_chromosomal=(data_output[data_output['id'].str.contains('_Chr')])
    filter_list = ['gyrA', 'parC']
    df_gyrA_and_parC = (data_output[data_output.gene.isin(filter_list)])
    ###Filter the gyrA and parC dataframe to show only those that contain snps in the positions listed below and assign this to a new dataframe
    gyrA_parC_snps = ['248-C-T', '259-G-A-','239-G-T-']
    gyrA_parC_cip = df_gyrA_and_parC['annotation'].str.contains('|'.join(gyrA_parC_snps))
    df_gyrA_parC_cip = df_gyrA_and_parC[gyrA_parC_cip]
    ###Filter multiple ant3, keeping just the longest version if both are present
    ant3_filter = (data_output[data_output['gene'].str.contains("ant3")])
    ant3_filter_long = ant3_filter.loc[ant3_filter.groupby('gene')['mapped_len'].idxmax()]
    ###Delete the original ampP, gyrA, parC, tet34 and ant3 rows from the original dataframe and merge ampP, gyrA or parC that passed the filters in ampP_snps_stringent or gyrA_parC_snps
    merge = drop_ampP_gyrA_parC,tet34_filter,df_gyrA_parC_cip,df_ampP_filter_snps,ant3_filter_long
    filtered_gyrA_parC_ampP = pd.concat(merge)
else:
    filtered_gyrA_parC_ampP=data_gene_filtered

if database_type=="AMR":
    ###Using gene and antimicrobial EFSA dictions to make another column with the AMR conferred by the gene
    test_dict_df = pd.read_csv(efsa_dict)
    df_as_dict = test_dict_df.set_index('id').T.to_dict('list')
    filtered_gyrA_parC_ampP['antimicrobial']= filtered_gyrA_parC_ampP['id'].map(df_as_dict)
    # Set output columns
    output_columns = list(data_raw)
    output_columns.insert(1,'gene')
    output_columns.insert(2,'class')
    output_columns.insert(0,'strain')
    output_columns.insert(3,'antimicrobial')   
    filtered_gyrA_parC_ampP['antimicrobial'] = filtered_gyrA_parC_ampP['antimicrobial'].map(lambda x: str(x)[2:-2])
    #Replace 'a' (a carry over from NaN) with blanks
    filtered_gyrA_parC_ampP=filtered_gyrA_parC_ampP.replace({'a':''})
elif database_type=="VIR":
    ###Using gene and Virulence dictionary to make another column with the Virulence function conferred by the gene
    vir_dict_df = pd.read_csv(vir_dict)
    ###Select just the columns "id" and "Virulence function" and set to new dataframe "vir_dict_gene_function"
    vir_dict_gene_function = vir_dict_df[['id','Virulence_function']]
    ###Change this dataframe to a dictionary list that can be called later
    vir_dict_gene_function = vir_dict_gene_function.set_index('id').T.to_dict('list')
    ###Select just the columns "id" and "Associated_pathotypes" and set to new dataframe "vir_dict_pathotypes"
    vir_dict_pathotypes = vir_dict_df[['id','Associated_pathotypes']]
    ###Change this datafram to a dictionary that can be called later
    vir_dict_pathotypes = vir_dict_pathotypes.set_index('id').T.to_dict('list')
    ###Make two new columns in our Seqfinder output dataframe called "Virulence_function" and "Associated_pathotypes"
    ###using the dictionaries we created to search for 'id' (the genes in our isolate)
    ###and match them with the associated keys in our dictionaries
    filtered_gyrA_parC_ampP['Virulence_function']= filtered_gyrA_parC_ampP['id'].map(vir_dict_gene_function)
    filtered_gyrA_parC_ampP['Associated_pathotypes']= filtered_gyrA_parC_ampP['id'].map(vir_dict_pathotypes)
    #Clean up the columns to only include the text and no brackets
    filtered_gyrA_parC_ampP['Virulence_function'] = filtered_gyrA_parC_ampP['Virulence_function'].map(lambda x: str(x)[2:-2])
    filtered_gyrA_parC_ampP['Associated_pathotypes'] = filtered_gyrA_parC_ampP['Associated_pathotypes'].map(lambda x: str(x)[2:-2])
    #Replace 'a' (a carry over from NaN) with blanks
    filtered_gyrA_parC_ampP=filtered_gyrA_parC_ampP.replace({'a':''}) 
    # Set output columns
    output_columns = list(data_raw)
    output_columns.insert(1,'gene')
    output_columns.insert(2,'Virulence_function')
    output_columns.insert(0,'strain')
    output_columns.insert(3,'Associated_pathotypes')
elif database_type=="DIS":
    ###Using gene and Virulence dictionary to make another column with the Virulence function conferred by the gene
    dis_dict_df = pd.read_csv(dis_dict)
    ###Select just the columns "id" and "Class" and set to new dataframe "dis_dict_gene_class"
    dis_dict_gene_class = dis_dict_df[['id','Class']]
    ###Change this dataframe to a dictionary list that can be called later
    dis_dict_gene_class = dis_dict_gene_class.set_index('id').T.to_dict('list')
    ###Select just the columns "id" and "Phenotype" and set to new dataframe "dis_dict_phenotype"
    dis_dict_phenotype = dis_dict_df[['id','Phenotype']]
    ###Change this dataframe to a dictionary that can be called later
    dis_dict_phenotype = dis_dict_phenotype.set_index('id').T.to_dict('list')
    ###Select just the columns "id" and "Function" and set to a new dataframe called "dis_dict_gene_function"
    dis_dict_function = dis_dict_df[['id','Function']]
    ###Change this dataframe to a dictionary that can be called later
    dis_dict_function = dis_dict_function.set_index('id').T.to_dict('list')
    ###Make three new columns in our Seqfinder output dataframe called "Class","Phenotype and "Function"
    ###using the dictionaries we created to search for 'id' (the genes in our isolate)
    ###and match them with the associated keys in our dictionaries
    filtered_gyrA_parC_ampP['Class']= filtered_gyrA_parC_ampP['id'].map(dis_dict_gene_class)
    filtered_gyrA_parC_ampP['Phenotype']= filtered_gyrA_parC_ampP['id'].map(dis_dict_phenotype)
    filtered_gyrA_parC_ampP['Function']= filtered_gyrA_parC_ampP['id'].map(dis_dict_function)
    #Clean up the columns to only include the text and no brackets
    filtered_gyrA_parC_ampP['Class'] = filtered_gyrA_parC_ampP['Class'].map(lambda x: str(x)[2:-2])
    filtered_gyrA_parC_ampP['Phenotype'] = filtered_gyrA_parC_ampP['Phenotype'].map(lambda x: str(x)[2:-2])
    filtered_gyrA_parC_ampP['Function'] = filtered_gyrA_parC_ampP['Function'].map(lambda x: str(x)[2:-2])
    #Replace 'a' (a carry over from NaN) with blanks
    #filtered_gyrA_parC_ampP=filtered_gyrA_parC_ampP.replace({'a':''}) 
    # Set output columns
    output_columns = list(data_raw)
    output_columns.insert(1,'gene')
    #output_columns.insert(2,'Class')
    output_columns.insert(0,'strain')
    output_columns.insert(3,'Phenotype')
    output_columns.insert(4,'Function')

else:
    output_columns = list(data_raw)
    output_columns.insert(1,'gene')
    output_columns.insert(0,'strain')
# Assign a list of column headers to be output in the final csv. This list can be edited here to
output_df = filtered_gyrA_parC_ampP[output_columns].round(2)

# filtering rows by the per_ID when database_type=="nonAMR"
if database_type!="AMR":
    output_df=output_df.loc[output_df['perc_mapped'] > per_ID]


# Write dataframe to CSV with suffix '_good_snps.csv'
output_filename = sys.argv[1].replace('.csv','_good_snps.csv')
output_df.to_csv(output_filename, index=False)
if database_type=="AMR":
    output_filename_chromosomal =  sys.argv[1].replace('.csv','_good_snps_only_chromosomal.csv')
    data_output_chromosomal.to_csv(output_filename_chromosomal, index=False)

