#!/usr/bin/env python
# -*- coding: utf-8 -*-

#IDEAS: introduce -test, which enables certain testing output in the wrapper.js, simply insert a "var testing_output" at the end of the wrapper and make the output dependent on "if (testing_output)"

import sys
import os
import shutil
from bs4 import BeautifulSoup
from HTMLParser import HTMLParser
from m20_analyse_apk import APK_analyser                    

def adm_print(msg):
    # print an administrative message: errors, progress ...
    global quite
    if (not quite):
        sys.stderr.write(str(msg)+"\n")

def inject_cordova(aa):
    global pol_path
    global interactive
    adm_print("------------injecting wrapper into cordova: ---------")
    if (aa.find_cordova() != 0):
        adm_print("error seearching for cordova-library")
        exit(1)
    cors = aa.cordova_abs
    adm_print("Found cordova libraries in:")
    adm_print(cors)
    for fname in cors:
        adm_print("Injection policy into " + fname)
        if (not os.path.isfile(fname)):
            adm_print("Cordova library at " + fname + " not found")
            exit(1)
#            adm_print("Cordova library at " + fname + " not found. Are you in a development directory?")
#            cor_fname = os.path.basename(fname)
#            cor_cand = "../platforms/android/platform_www/" + cor_fname
#            if (os.path.isfile(cor_cand)):
#                adm_print("File found at " + cor_cand)
#                fname = cor_cand
#            else:
#                adm_print("File not found -> going to next one")
#                continue
        cor_file = open(fname,"a")
        wrapper_file = open(pol_path+"/cordova_wrapper.js")
        cor_file.write(wrapper_file.read())
        cor_file.close()
        wrapper_file.close()
    adm_print("Done")

def create_wrapper(wrapper_filename,policy_filename,script_filename):
    global creation
    global mark
    wrapper_file = open(wrapper_filename,'r');
    policy_file = open(policy_filename,'r');
    script_file = open(script_filename,'w');
    for i in range(8):
        script_file.write(wrapper_file.readline());
    wrapper_file.readline(); #absorb the stub
    script_file.write(policy_file.read());
    if (creation):
        script_file.write("\n var policy_creation = true;\n");
    if (mark):
        script_file.write("\n var policy_mark = true;\n");
    script_file.write(wrapper_file.read());
    
def inject_html(aa):
    global pol_path
    global wrapper_pos
    global policy_filename
    adm_print("-------------injecting wrapper into html-----------------")
    adm_print("Policy file specified at " + policy_filename)
    pol = "<script src='wrapper.js'></script>"
    create_wrapper("wrapper_res/wrapper.js",policy_filename,aa.get_html_dir()+"/wrapper.js")
#    shutil.copyfile(policy_filename,aa.get_html_dir()+"/wrapper.js")
    wrapper = BeautifulSoup(pol).find("script")
    aa.html_tree.head.insert(wrapper_pos,wrapper)
    wrapper_pos = wrapper_pos + 1
    adm_print("Done")


# global values for argument parsing
arg_pos = 1               # next argument to consider
expect_options = True     # Are we still parsing options?

# Global value for reordering
wrapper_pos = 0            # child index where the filter is inserted into the <head>

# values for the options
interactive = False       # Is the policification interactive?
policy_filename = ""
quite = False
creation = False
mark = False

while (expect_options):
    if (len(sys.argv)-1<=arg_pos):
        expect_options = False
        continue
    if (sys.argv[arg_pos] == "-i"):
        interactive = True
        arg_pos = arg_pos +1
        continue
    if (sys.argv[arg_pos] == "-p"):
        arg_pos = arg_pos +1
        if (len(sys.argv)-1<=arg_pos):
            print "Path for policy file expected after -p"
            continue
        policy_filename = sys.argv[arg_pos]
        if (not os.path.isfile(policy_filename)):
            print "File " + policy_filename + " not found"
            policy_filename = ""
        arg_pos = arg_pos + 1
        continue
    if (sys.argv[arg_pos] == "-q"):
        quite = True
        arg_pos = arg_pos + 1
        continue
    if (sys.argv[arg_pos] == "-c"):
        creation = True
        arg_pos = arg_pos + 1
        continue
    if (sys.argv[arg_pos] == "-m"):
        mark = True
        print "mark found"
        arg_pos = arg_pos + 1
        continue
    # else
    print "Argument " + sys.argv[arg_pos] + " not recognised"
    arg_pos = arg_pos +1

if (len(sys.argv)<=arg_pos):
    print  __file__ + " [options] <root_dir>"
    exit(0)

if (policy_filename == ""):
    policy_filename = "wrapper_res/empty.pol"
    print "Policy file not specified, falling back to default location: " + policy_filename
    
print "Scanning for files"    
aa = APK_analyser(sys.argv[arg_pos])
if (aa.parse_index() != 0):
    print "main html could not be identified"
    exit(0)

pol_path = os.path.abspath(os.path.dirname(sys.argv[0]))+ "/wrapper_res"
            
#reorder_jQuery(aa)
#inject_cordova(aa)
inject_html(aa)

f=open(aa.index_html_abs,"w")
f.write(aa.html_tree.prettify("utf-8"))
f.close()
