import os
import re
import sys

max_parallel_task_number = 20


# Env req: LTR_Annotation_py2

class IndividualAccession(object):
    def __init__(self, genome_fa, telib_fa, genome_gff, te_gff, seq_tr_tab, te_sum, align_bam_folder):
        """

        :param genome_fa:
        :param telib_fa:
        :param genome_gff: Genome annotation, presented as 'genomic.gff' located in the accession root folder.
        :param te_gff:
        :param seq_tr_tab:
        :param te_sum:
        :param align_bam_list:
        :param accession_name:
        """
        self._genome_fa = genome_fa
        self._telib_fa = telib_fa
        self._genome_gff = genome_gff
        self._te_gff = te_gff
        self._seq_tr_tab = seq_tr_tab
        self._te_sum = te_sum
        self._align_bam_folder = align_bam_folder

        # Root folder for the project, containing all links.
        self._accession_name = os.getcwd().split("/")[-1]
        self._current_dir = os.getcwd() + "/"
        # bam-style alignment file for a certain species
        self._alignment_bam_dir_list = []

    def link_files_and_init(self):
        # Make a directory named by accession_id and the function will automatically make link from original data.

        ori_directory = '/data5/Andropogoneae_LTR_Project/Step0_Genome_Download/' + self._accession_name
        current_dir = self._current_dir

        # FASTA files
        genome_fa = ori_directory + "/" + self._accession_name + ".fa"
        telib_fa = ori_directory + "/" + self._accession_name + ".fa.mod.EDTA.TElib.fa"
        genome_fa_dest = current_dir + self._accession_name + "_genome.fa"
        telib_fa_dest = current_dir + self._accession_name + "_telib.fa"

        os.system("ln -s %s %s" % (genome_fa, genome_fa_dest))
        os.system("ln -s %s %s" % (telib_fa, telib_fa_dest))
        self._genome_fa = genome_fa_dest
        self._telib_fa = telib_fa_dest

        # Annotation files
        genome_gff = ori_directory + "/genomic.gff"
        te_gff = ori_directory + "/" + self._accession_name + ".fa.mod.EDTA.TEanno.gff3"
        genome_gff_dest = current_dir + self._accession_name + "_genome.gff"
        te_gff_dest = current_dir + self._accession_name + "_te.gff3"

        os.system("ln -s %s %s" % (genome_gff, genome_gff_dest))
        os.system("ln -s %s %s" % (te_gff, te_gff_dest))
        self._genome_gff = genome_gff_dest
        self._te_gff = te_gff_dest

        # Other critical files
        seq_tr_tab = ori_directory + "/" + self._accession_name + "_FA_sequence_id_translation/" + self._accession_name + ".fa.translation.tab"
        te_sum = ori_directory + "/" + self._accession_name + ".fa.mod.EDTA.TEanno.sum"
        seq_tr_tab_dest = current_dir + self._accession_name + "_seqtr.tab"
        te_sum_dest = current_dir + self._accession_name + "_te.sum"

        os.system("ln -s %s %s" % (seq_tr_tab, seq_tr_tab_dest))
        os.system("ln -s %s %s" % (te_sum, te_sum_dest))
        self._seq_tr_tab = seq_tr_tab_dest
        self._te_sum = te_sum_dest

        # =======================================
        # Make folder for downstream analysis
        # =======================================
        # For command-line bash scripts taking advantage of multitasking
        os.system("mkdir %s" % current_dir + "tmp_instructions")
        # LTR classification module - TEsorter
        os.system("mkdir %s" % current_dir + "Module2_LTR_domain_classification")
        # TE expression module - TEtranscripts
        os.system("mkdir %s" % current_dir + "Module6_TE_expression")
        os.system("mkdir %s" % current_dir + "Module6_TE_expression/Alignment_bam")
        os.system("mkdir %s" % current_dir + "Module6_TE_expression/TEcount_raw")
        os.system("mkdir %s" % current_dir + "Module6_TE_expression/TEcount_normalized")
        os.system("mkdir %s" % current_dir + "Module6_TE_expression/TEcount_final")

        # Identify alignment BAM files
        if self._align_bam_folder.endswith("/"):  # The original location for BAM files
            self._align_bam_folder.rstrip("/")
        try:
            for indv_file in os.listdir(self._align_bam_folder):  # ex. 1.bam
                if indv_file.endswith(".bam"):
                    os.system("ln -s %s %s" % (self._align_bam_folder + "/" + indv_file,
                                               current_dir + "Module6_TE_expression/Alignment_bam/" + indv_file))
                    self._alignment_bam_dir_list.append(current_dir + "Module6_TE_expression/Alignment_bam/" + indv_file)
        except OSError:
            print("bam folder not found, skipping.")

    def module6_TE_expression(self):

        # ============================================================================
        # Convert general GFF-style annotation file to TEcount-compatible GTF style.
        # ============================================================================
        global indv_file

        def sequence_trans_dict_construct(translation_tab):

            # Construct mapping for chr sequences
            # generate dict, Seq1 (line 1 in TE GFF) -> NC_012879.2 (line 1 in gene annotation GFF)
            # for only the chromosomes and contigs

            chr_idtf_re = re.compile(r'^.*[Cc]hromosome (?P<chr_id>\d+),.*$')
            ctg_idtf_re = re.compile(r'^.*genomic scaffold,.*$')
            ctg_idtf_re_b73v4 = re.compile(r'^.*genomic scaffold,.*B73V4_ctg(?P<ctg_id>\d+).*$')
            content_type = 'B73V4'

            _tmp_seq_translation_dict_fwd = {}  # Seq1 (line 1 in TE GFF) -> chr1
            _tmp_seq_translation_dict_rev = {}  # chr1 -> Seq1 (line 1 in TE GFF)
            _tmp_seq_translation_dict_fwd2 = {}  # Seq1 (line 1 in TE GFF) -> NC_012879.2
            _tmp_seq_translation_dict_rev2 = {}  # NC_012879.2 -> Seq1 (line 1 in TE GFF)
            try:
                with open(translation_tab, mode='r') as entries:
                    for entry in entries:
                        if content_type == 'B73V4':
                            if re.search(chr_idtf_re, entry.split("\t")[1]):
                                search_group = re.search(chr_idtf_re, entry.split("\t")[1])
                                _tmp_seq_translation_dict_fwd[entry.split("\t")[0]] = 'Chr' + search_group.group(
                                    'chr_id')
                                _tmp_seq_translation_dict_rev['Chr' + search_group.group('chr_id')] = entry.split("\t")[
                                    0]
                                print(entry.split("\t")[0], 'Chr' + search_group.group('chr_id'))

                            elif re.search(ctg_idtf_re_b73v4, entry.split("\t")[1]):
                                search_group = re.search(ctg_idtf_re_b73v4, entry.split("\t")[1])
                                _tmp_seq_translation_dict_fwd[entry.split("\t")[0]] = 'B73V4_ctg' + search_group.group(
                                    'ctg_id')
                                _tmp_seq_translation_dict_rev['B73V4_ctg' + search_group.group('ctg_id')] = \
                                    entry.split("\t")[0]
                                print(entry.split("\t")[0], 'B73V4_ctg' + search_group.group('ctg_id'))
                        else:
                            if re.match(chr_idtf_re, entry.split("\t")[1]):
                                _tmp_seq_translation_dict_fwd2[entry.split("\t")[0]] = entry.split("\t")[1].split(" ")[
                                    0]
                                _tmp_seq_translation_dict_rev2[entry.split("\t")[1].split(" ")[0]] = entry.split("\t")[
                                    0]
                                print(entry.split("\t")[1], entry.split("\t")[1].split(" ")[0])

                            elif re.match(ctg_idtf_re, entry.split("\t")[1]):
                                _tmp_seq_translation_dict_fwd2[entry.split("\t")[0]] = entry.split("\t")[1].split(" ")[
                                    0]
                                _tmp_seq_translation_dict_rev2[entry.split("\t")[1].split(" ")[0]] = entry.split("\t")[
                                    0]
                                print(entry.split("\t")[1], entry.split("\t")[1].split(" ")[0])
            except FileNotFoundError:
                exit('seq translation tab %s not found' % translation_tab)
            return _tmp_seq_translation_dict_fwd, _tmp_seq_translation_dict_rev, _tmp_seq_translation_dict_fwd2, \
                   _tmp_seq_translation_dict_rev2

        def edta_GFF3_to_TETr_GTF(EDTA_GFF3, TETr_GTF_out, seq_translation_fwd):
            """
            :param seq_translation_fwd:
            :param TETr_GTF_out:
            :param EDTA_GFF3:
            :param TETr_GTF: output directory for transformed GTF file
            """
            try:
                with open(EDTA_GFF3, mode='r') as in_fh:
                    with open(TETr_GTF_out, mode='w') as out_fh:
                        for entry in in_fh:
                            if not entry.startswith("#"):  # Filter comment lines
                                gff_entry_split_list = entry.split("\t")

                                if gff_entry_split_list[2] not in ["repeat_region", "target_site_duplication",
                                                                   "long_terminal_repeat"]:
                                    # Filter intact-LTR flanking annotation entries
                                    try:
                                        if seq_translation_fwd[gff_entry_split_list[0]]:
                                            # Filter interested regions, typically chromosomes and major contigs.

                                            gtf_entry_list = [
                                                seq_translation_fwd[gff_entry_split_list[0]],
                                                # chr name, in chrN/ctgN format
                                                gff_entry_split_list[1],  # EDTA
                                                'exon',
                                                gff_entry_split_list[3], gff_entry_split_list[4],  # start, end
                                                gff_entry_split_list[5], gff_entry_split_list[6],
                                                gff_entry_split_list[7],
                                                # strand info, etc.
                                            ]

                                            gff_entry_infoarea_split_list = gff_entry_split_list[-1].rstrip("\n").split(
                                                ";")
                                            gff_entry_infoarea_dict = {}
                                            for indv_info in gff_entry_infoarea_split_list:
                                                gff_entry_infoarea_dict[indv_info.split("=")[0]] = indv_info.split("=")[
                                                    1]

                                            # gene_id "MER77B"; transcript_id "MER77B_dup45"; family_id "ERVL";
                                            # class_id "LTR";
                                            gtf_entry_list.append(
                                                "gene_id \"%s\";"  # Compare expression at a family level
                                                " transcript_id \"%s\";"
                                                " family_id \"%s\";"  # Super-family
                                                " class_id \"%s\";\n" % (gff_entry_infoarea_dict['Name'],
                                                                         gff_entry_infoarea_dict['ID'],
                                                                         gff_entry_infoarea_dict['Name'],
                                                                         gff_entry_infoarea_dict[
                                                                             'Classification']))
                                            out_fh.write("\t".join(gtf_entry_list))
                                    except KeyError:
                                        continue
                        print("All done for TE GTF.")
            except FileNotFoundError:
                return Exception

        def genome_GFF3_to_TETr_GTF_B73(GENOME_GFF3, TETr_GTF_out, seq_translation_rev):
            """
            :param seq_translation_rev:
            :param TETr_GTF_out:
            :param GENOME_GFF3:
            :param TETr_GTF: output directory for transformed GTF file
            """
            with open(GENOME_GFF3, mode='r') as in_fh:
                with open(TETr_GTF_out, mode='w') as out_fh:
                    for entry in in_fh:
                        if not entry.startswith("#"):  # Filter comment lines
                            gff_entry_split_list = entry.split("\t")

                            if gff_entry_split_list[2] in ["exon", "CDS", "three_prime_UTR", "five_prime_UTR"]:
                                # Filter entries
                                try:
                                    if seq_translation_rev[gff_entry_split_list[0]]:
                                        # Filter interested regions, typically chromosomes and major contigs.
                                        # chr1 -> Seq1 (line 1 in TE GFF)
                                        # DICT1 is used
                                        if gff_entry_split_list[2] == "three_prime_UTR":
                                            gff_entry_split_list[2] = "3UTR"
                                        elif gff_entry_split_list[2] == "five_prime_UTR":
                                            gff_entry_split_list[2] = "5UTR"

                                        gtf_entry_list = [
                                            gff_entry_split_list[0],  # chr name
                                            gff_entry_split_list[1],  # identifier
                                            gff_entry_split_list[2],  # exon, CDS, etc.
                                            gff_entry_split_list[3], gff_entry_split_list[4],  # start, end
                                            gff_entry_split_list[5], gff_entry_split_list[6],
                                            gff_entry_split_list[7],
                                            # strand info, etc.
                                        ]

                                        # Creating standard line 9 like this: gene_id "LYRM2"; transcript_id
                                        # "NM_020466"; exon_number "1"; exon_id "NM_020466.1"; gene_name "LYRM2";

                                        gff_entry_infoarea_split_list = gff_entry_split_list[-1].rstrip("\n").split(
                                            ";")
                                        gff_entry_infoarea_dict = {}
                                        for indv_info in gff_entry_infoarea_split_list:
                                            gff_entry_infoarea_dict[indv_info.split("=")[0]] = indv_info.split("=")[
                                                1]

                                        if gff_entry_split_list[2] == "exon":
                                            gtf_entry_list.append("gene_id \"%s\";"
                                                                  " transcript_id \"%s\";"
                                                                  " exon_number \"%s\";"
                                                                  " exon_id \"%s\";"
                                                                  " gene_name \"%s\";\n" % (
                                                                      gff_entry_infoarea_dict['Name'].split("_")[0],
                                                                      gff_entry_infoarea_dict['Name'].split(".")[0],
                                                                      gff_entry_infoarea_dict['Name'].split(".")[
                                                                          0].lstrip(
                                                                          "exon"),
                                                                      gff_entry_infoarea_dict['exon_id'],
                                                                      gff_entry_infoarea_dict['Name'].split("_")[0],
                                                                  ))
                                        else:  # CDS, 5'UTR, 3'UTR
                                            gtf_entry_list.append("gene_id \"%s\";"
                                                                  " transcript_id \"%s\";"
                                                                  " exon_number \"%s\";"
                                                                  " exon_id \"%s\";"
                                                                  " gene_name \"%s\";\n" % (
                                                                      gff_entry_infoarea_dict['Parent'].split(":")[
                                                                          1].split(
                                                                          "_")[0],
                                                                      gff_entry_infoarea_dict['Parent'].split(":")[
                                                                          1],
                                                                      "0",
                                                                      "0",
                                                                      gff_entry_infoarea_dict['Parent'].split(":")[
                                                                          1].split(
                                                                          "_")[0],
                                                                  ))

                                        out_fh.write("\t".join(gtf_entry_list))
                                except KeyError:
                                    # print("Key not found for ", gff_entry_split_list[0])
                                    continue
                    print("All done for gene GTF.")

        print("Parsing seq translation tab and constructing meaningful sequence dicts.")
        # generate dict, Seq1 (line 1 in TE GFF) -> NC_012879.2 (line 1 in gene annotation GFF)
        seq_translation_dict_fwd, seq_translation_dict_rev, seq_translation_dict_fwd2, seq_translation_dict_rev2 = \
            sequence_trans_dict_construct(self._seq_tr_tab)
        print("Done")

        # Output position for converted GTFs: Module6_TE_expression/
        print("Converting original TE GFF to TEcount-compatible GTF")
        edta_GFF3_to_TETr_GTF(self._te_gff, self._current_dir + "Module6_TE_expression/TE_annot_converted.gtf",
                              seq_translation_dict_fwd)
        print("Done.")
        print("Converting original gene GFF to TEcount-compatible GTF")
        print(self._genome_gff)
        genome_GFF3_to_TETr_GTF_B73(self._genome_gff,
                                    self._current_dir + "Module6_TE_expression/genome_annot_converted.gtf",
                                    seq_translation_dict_rev)
        print("Done.")
        print("Deploying TEcount tasks, max threads:", max_parallel_task_number)
        # ============================================================================
        # Running TEcount pipeline: generating count tables
        # ============================================================================
        tecount_command_list = []
        break_counter = 0  # Indicate the break for multitasking
        for indv_bam in self._alignment_bam_dir_list:

            tecount_command = ("mkdir %s && cd %s && "
                               "TEcount --mode multi --TE %s --GTF %s --project %s -b %s --sortByPos && "
                               "mv %s %s && "
                               "cd .. && rm -r %s "
                               "&\n" % (
                                   self._current_dir + "Module6_TE_expression/" + indv_bam.split("/")[-1].split("V")[0],
                                   self._current_dir + "Module6_TE_expression/" + indv_bam.split("/")[-1].split("V")[0],
                                   self._current_dir + "Module6_TE_expression/TE_annot_converted.gtf",
                                   self._current_dir + "Module6_TE_expression/genome_annot_converted.gtf",
                                   self._accession_name,
                                   indv_bam,
                                   self._current_dir + "Module6_TE_expression/" + indv_bam.split("/")[-1].split("V")[
                                       0] + "/" + self._accession_name + ".cntTable",
                                   self._current_dir + "Module6_TE_expression/TEcount_raw/" +
                                   indv_bam.split("/")[-1].split("V")[0] + ".cntTable",
                                   self._current_dir + "Module6_TE_expression/" + indv_bam.split("/")[-1].split("V")[0]
                               ))
            tecount_command_list.append(tecount_command)
            break_counter += 1

            if break_counter == max_parallel_task_number:
                tecount_command_list.append("wait\n")
                break_counter = 0
                # break  # For diagnosis
        try:
            with open(self._current_dir + "tmp_instructions/tecount_batch.sh", mode='w') as out_fh:

                # Switching to the TE expression subdir
                out_fh.write("cd %s\n" % self._current_dir + "Module6_TE_expression/TEcount_raw/")
                # Activate env containing TEtranscripts, python=2.7
                out_fh.write("source /home/test3/miniconda3/etc/profile.d/conda.sh\n")
                out_fh.write("conda activate LTR_Annotation_py2\n")

                for indv_command in tecount_command_list:
                    out_fh.write(indv_command)
        except:
            exit("Error occurred when writing batch command used for TEcount.")

        print("Successfully wrote %d tasks.\nExecuting commands.." % len(tecount_command_list))
        os.system("sh %s" % self._current_dir + "tmp_instructions/tecount_batch.sh")  # Execute command
        print("Execution of TEcount pipeline has completed for all bam files.")

        # ============================================================================
        # Standardizing count table output and measure the length of TEs (on a family level) and genes (all exons)
        # ============================================================================

        # Count feature length using converted GTF files
        def length_counter(TE_GTF, genome_GTF, TEout_lenTable, Geneout_lenTable):
            """

            :param Geneout_lenTable:
            :param TEout_lenTable:
            :param TE_GTF:
            :param genome_GTF:
            :return:
            """
            fam_length_dict = {}  # fam_name -> total_len
            gene_length_dict = {}  # gene_name -> sum of all exon len
            print("Processing TE GTF")
            with open(TE_GTF, mode='r') as in_fh:
                for entry in in_fh:
                    entry_split_list = entry.split("\t")

                    gtf_entry_infoarea_split_list = entry_split_list[-1].rstrip("\n").split(";")
                    gtf_entry_infoarea_dict = {}
                    for indv_info in gtf_entry_infoarea_split_list:
                        if len(indv_info.split("\"")) == 3:
                            gtf_entry_infoarea_dict[indv_info.split('\"')[0].rstrip(' ').lstrip(' ')] = \
                                indv_info.split('\"')[1]
                    # print(entry)
                    # print(gtf_entry_infoarea_dict.keys())
                    try:
                        if fam_length_dict[gtf_entry_infoarea_dict['family_id']]:
                            fam_length_dict[gtf_entry_infoarea_dict['family_id']] += int(entry_split_list[4]) - int(
                                entry_split_list[3])
                    except KeyError:
                        fam_length_dict[gtf_entry_infoarea_dict['family_id']] = int(entry_split_list[4]) - int(
                            entry_split_list[3])
            print("Processing gene GTF")
            with open(genome_GTF, mode='r') as in_fh:
                for entry in in_fh:
                    entry_split_list = entry.split("\t")
                    if entry_split_list[2] == 'exon':

                        gtf_entry_infoarea_split_list = entry_split_list[-1].rstrip("\n").split(";")
                        gtf_entry_infoarea_dict = {}
                        for indv_info in gtf_entry_infoarea_split_list:
                            if len(indv_info.split("\"")) == 3:
                                gtf_entry_infoarea_dict[indv_info.split('\"')[0].rstrip(' ').lstrip(' ')] = \
                                    indv_info.split('\"')[1]

                        try:
                            if gene_length_dict[gtf_entry_infoarea_dict['gene_id']]:
                                gene_length_dict[gtf_entry_infoarea_dict['gene_id']] += int(entry_split_list[4]) - int(
                                    entry_split_list[3])
                        except KeyError:
                            gene_length_dict[gtf_entry_infoarea_dict['gene_id']] = int(entry_split_list[4]) - int(
                                entry_split_list[3])

            with open(TEout_lenTable, mode='w') as out_fh:
                for ename, elen in fam_length_dict.items():
                    out_fh.write(ename + "\t" + str(elen) + "\n")
            with open(Geneout_lenTable, mode='w') as out_fh:
                for ename, elen in gene_length_dict.items():
                    out_fh.write(ename + "\t" + str(elen) + "\n")
            print("Done processing GTF")

        print("Counting feature length for converted TE GTF and gene GTF")
        length_counter(self._current_dir + "Module6_TE_expression/TE_annot_converted.gtf",
                       self._current_dir + "Module6_TE_expression/genome_annot_converted.gtf",
                       self._current_dir + "Module6_TE_expression/TE_family.length",
                       self._current_dir + "Module6_TE_expression/genome_gene.length")
        print("Done.")


if len(sys.argv) == 2:
    mainAccession = IndividualAccession("", "", "", "", "", "", sys.argv[1])
    mainAccession.link_files_and_init()
    mainAccession.module6_TE_expression()

elif len(sys.argv) == 1:  # Make link only, for species that lack RNA-seq datasets.
    mainAccession = IndividualAccession("", "", "", "", "", "", "")
    mainAccession.link_files_and_init()
else:
    print("Env req: LTR_Annotation_py2")
    print("Usage: python3 [This Script] [Folder to .bam Files]")
