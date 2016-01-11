#!/usr/bin/env python
import sys
import os
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import subprocess

def adm_print(msg):
    # print an administrative message: errors, progress ...
    global quite
    if (not quite):
        sys.stderr.write( str(msg) + "\n" )

class APK_analyser:
    def __init__(self,rootdir):

        self.rootdir = rootdir # root directory of app to be analysed
        self.index_html_abs = "" # absolute path to index.html used
        self.pg_version = ""   # PhoneGap version (as far as known) possibilities "<2.0" ">2.0" "amb"
        self.html_parsed = False # is self.html_tree already popularised

        self.config_abs = []   # absolute paths to config.xml
        self.manifest_abs = [] # absolute paths to Manifests
        self.cordova_abs = []  # absolute paths to cordova libraries used in index
        self.jquery_abs = []   # absolute paths to jQuery libraries udes in index
        self.jquery_rel = []   # path to jQuery Libs relative to index.html

        self.plugins = []
        self.permissions = []
        self.buttons = []
    def ask_cand(self,lib,path):
        answer = ""
        while (answer == ""):                                                      
            answer = raw_input("Expect " + lib + " library in " + path + " ? [Y,n]").lower()
            if (answer == "") or (answer == "y"):                                  
                answer = "y"                                                       
            elif (answer == "n"):                                                  
                continue                                                           
            else:                                                   
                answer = ""
        return (answer == "y")
    def postprocess(self,lib,list):
        # returns the error code
        # if there is no candidate found -> return 1
        # if there are multiple candidates ->
        #    ask for each candidate if interactive is enabled
        #    return 2, if still multiple files are possible
        global interactive
        if (list == []):
            adm_print("No candidate found for " + lib)
            return 1
        if (len(list)>1):
            if (interactive):
                for c in list:
                    if (not self.ask_cand(lib,c)):
                        list.remove(c)
        if (len(list)>1):
            adm_print("Multiple candidates found for " + lib)
            return 2
        return 0
    
    def find_config(self):
        # finds all candidates for the config file,
        # stores the complete paths relative to the executing dir in config_abs
        # returns 0 if successful, error code otherwise 
        # Possible errors: 1 Config file not found
        #                  2 multiple config files found

        # already looked for?
        if (self.config_abs != []):
            return 0
        # find candidates
        for root,dirs,files in os.walk(self.rootdir):
            for file in files:
                if (file == "config.xml"):
                    self.config_abs.append(os.path.join(root,file));
                    self.add_pg_version(">2.0")
                if (file == "plugins.xml"):
                    self.config_abs.append(os.path.join(root,file));
                    self.add_pg_version("<2.0")
                if (file == "cordova.xml"):
                    self.config_abs.append(os.path.join(root,file));
                    self.add_pg_version("<2.0")
        # result postprocessing
        return self.postprocess("config.xml",self.config_abs)
                        
    def find_Manifest(self):
        # finds all candidates for the AndroidManifest.xml file.
        # stores the complete paths relative to the executing dir in manifest_abs
        # returns 0 if successful, error code otherwise
        # possible errors: 1 Manifest not found
        #                  2 multiple candidates found

        # don't do it again
        if (self.manifest_abs != []):
            return 0
        # find all candidates
        for root,dir,files in os.walk(self.rootdir):
            for file in files:
                if (file == "AndroidManifest.xml"):
                    self.manifest_abs.append(os.path.join(root,file))
        # result postprocessing
        return self.postprocess("AndroidManifest.xml",self.manifest_abs)
    
    def add_pg_version(self,new):
        if (self.pg_version == ""):
            self.pg_version = new
        elif (self.pg_version != new):
            self.pg_version = "amb" #ambigue
    def get_pg_version(self):
        self.find_config() # can handle the error states
        return self.pg_version
    
    def extract_plugins(self,root):
        # extracts the plugins from a parsed config.xml or plugins.xml
        plugins = []
        for elem in root:
            if (elem.tag.find("feature")>-1):
                for line in elem:
                    if (line.tag.find("param")>-1):
                        if (line.get('name')=="android-package"):
                            plugins.append(line.get('value'))
            if (elem.tag.find("plugins")>-1):
                for line in elem:
                    if (line.tag.find("plugin")>-1):
                        plugins.append(line.get('value'))
        if (root.tag.find("plugins")>-1):
            for line in root:
                if (line.tag.find("plugin")>-1):
                    plugins.append(line.get('value'))
        return plugins
        
    def get_plugins(self):
        # find the config.xml/plugins.xml file and extract the plugins from it.
        # return 1 if no parsable config.xml was found
        
        self.find_config() # can handle the error states later

        plugins = []
        for c in self.config_abs:
            try:
                tree = ET.parse(c)
                root = tree.getroot()
                plugins = plugins + self.extract_plugins(root)
            except:
                adm_print("Could not parse Config: " + c)
                self.config_abs.remove(c)
        if (self.config_abs == []):
            adm_print("No parsable config file found")
            return 1
        return plugins

    def get_permissions(self):
        # find the Manifest file and extract the permissions from it
        # return 1 if no parsable AndroidManifest was found
        
        self.find_Manifest() # can handle the error states 

        permissions = []
        for c in self.manifest_abs:
            try:
                tree = ET.parse(c)
                root = tree.getroot()
                
                for elem in root:
                    if (elem.tag == "uses-permission"):
                        for (name,value) in elem.items():
                            if name.find("name"):
                                permissions.append(value)
            except:
                adm_print("Could not parse Manifest: " + c)
        if (self.manifest_abs == []):
            adm_print("No parsable AndroidManifest found")
            return 1
        return permissions

    def find_index(self):
        # find the index.html file in the config.xml.
        # if the file is ambigiouse the value of self.index_html_abs will be "amb" afterwards
        # if there is not a unique index.html, return value will -1, 0 otherwise
        # returns 0 if everything goes well, error code otherwise
        # errorcodes: 1 -> no candidate for index.html found
        #             2 -> multiple candidates found
        if (self.index_html_abs != ""):
            if (self.index_html_abs == "amb"):
                return 2
            else :
                return 0
        self.find_config() # can handle error states

        for c in self.config_abs:
            try:
                tree = ET.parse(c)
                root = tree.getroot()

                for elem in root:
                    if (elem.tag.find("content")>-1):
                        candidate = elem.get("src")
                        if (self.index_html_abs == ""):
                            self.index_html_abs = self.rootdir + "/assets/www/" + candidate
                        elif (self.index_html_abs != candidate):
                            self.index_html_abs = "amb"
                            adm_print("Multiple main html candidates found")
                            return 2
            except:
                adm_print("Failed to parse Config: " + c)
                self.config_abs.remove(c)
        if (self.index_html_abs == ""):
            # if the config file does not mention content, then we have to seachr for the main html in the .smali files.
#            adm_print("No index found in the configs -> Search in smali files")
            ps = subprocess.Popen(["egrep","-hiro",'"file:///android_asset/.*html"'],stdout=subprocess.PIPE)
            line = ps.stdout.readline()
            cands = []
            while (line != ''):
                cand = self.rootdir+"/assets/"+ line[23:-2]
                if (os.path.isfile(cand)):
                    cands.append(cand)
                line = ps.stdout.readline()
            cands = list(set(cands))
            if (len(cands) == 1):
                self.index_html_abs = cands[0]
                return 0
            elif (len(cands) > 1):
                adm_print("Multiple main html candidates found: " + str(cands))
                return 2
            # nothing found at all -> assume default
            if (os.path.isfile(self.rootdir+"/assets/www/index.html") ):
                self.index_html_abs = self.rootdir+"/assets/www/index.html"
            else :
                adm_print("No main html candidate found")
                return 1
        return 0
    def get_html_dir(self):
        if (self.find_index() != 0):
            return ""
        else:
            return os.path.dirname(self.index_html_abs)
    def parse_index(self):
        # parse index.html into html_tree
        # returns 0 if everything goes well, errorcode otherwise
        # errorcodes: 1 -> No unique index found
        #             2 -> index failed to parse
        if (self.html_parsed):
            return 0
        if (self.find_index() != 0):
            return 1
        try:
            index_content = open(self.index_html_abs).read()
            self.html_tree = BeautifulSoup(index_content)
            self.html_parsed = True
        except:
            adm_print("Could not parse index.html at " + self.index_html_abs)
            return 2
        return 0

    def rem_WS(self,s):
        return " ".join(s.split())
    def get_buttons(self):
        # scan the main index for all clickable items in the html, store their content
        # clickables are considered: <a>, <button>, <input type="submit">
        # returns 1 for a error upstream, 0 otherwise
        if (self.parse_index() != 0):
            return 1
        clicks = []
        anchors = self.html_tree.find_all("a")
        for elem in anchors:
            clicks.append(self.rem_WS(elem.text))
        buttons = self.html_tree.find_all("button")
        for elem in buttons:
            clicks.append(self.rem_WS(elem.text))
        inputs = self.html_tree.find_all("input")
        for elem in inputs:
            if (elem.get("type") == "submit") or \
            (elem.get("type") == "button") or \
            (elem.get("type") == "image") or \
            (elem.get("type") == "reset") or \
            (elem.get("type") == "file"):
                clicks.append(self.rem_WS(elem.get("value")))
        return clicks
    
    def get_lib(self,lib):
        # return a list of all candidates for the lib
        # returns 1 for errors upstream
        # if interactive is set, ask for every found candidate, even if only one
        if (self.parse_index() != 0 ):
            return 1
        scripts = self.html_tree.find_all("script")                                             
        src_candidates = []
        src_cand_abs  = []
        for s in scripts:                                                                  
            if (s.get("src")):                                                             
                source = s.get("src")                                                      
                if (source.lower().find(lib)>=0):                                          
                    src_candidates.append(source)                                                   
        filtered = src_candidates                                                                
        if (interactive):                                                                  
            filtered = []                                                                  
            for jq in src_candidates:
                if (self.ask_cand(lib,self.get_html_dir() + "/" +jq)):
                    filtered.append(jq)
        for source in filtered:
            src_cand_abs.append(self.get_html_dir() + "/" + source)
        return {"rel":filtered,"abs":src_cand_abs}
    def find_jQuery(self):
        # scan the main html for included jQuery libraries
        # return 1 if something was wrong upstream, 0 otherwise
        if (self.jquery_abs != []):
            return 0
        cand = self.get_lib("jquery")
        if (cand == 1):
            return 1
        self.jquery_abs = cand["abs"]
        self.jquery_rel = cand["rel"]
        return 0
    def find_cordova(self):
        # scan the main html for included cordova libraries
        # return 1 if something was wrong, 0 otherwise
        if (self.cordova_abs != []):
            return 0
        cand = self.get_lib("cordova")
        
        if (cand != 1):
            self.cordova_abs.extend(cand["abs"])
        else:
            return 1
        
        cand = self.get_lib("phonegap")
        if (cand != 1):
            self.cordova_abs.extend(cand["abs"])
        else:
            return 1
        return 0
        
def analyse_humanReadable(dir):
    global aa  # global to query after execution of the main method
    aa = APK_analyser(dir)
    
    plugins = aa.get_plugins()
    if (plugins != 1):
        print "--------------------Plugins: --------------------"
        print plugins

    permissions = aa.get_permissions()
    if (permissions != 1):
        print "--------------------Permissions: --------------------"
        print permissions
        
    clicks = aa.get_buttons()
    if (clicks != 1):
        print "--------------------Clickables: --------------------"
        print clicks
    if (aa.find_cordova() != 1):
        print "--------------------cordova library found in --------------------"
        print aa.cordova_abs        
    if (aa.find_jQuery() != 1):
        print "--------------------jQuery library found in --------------------"
        print aa.jquery_abs
        
    print "Cordova version: " + aa.get_pg_version()

def analyse_csv(dir):
    global aa
    global filter_useable
    
    aa = APK_analyser(dir)
    if (filter_useable) and (not is_useable(aa)):
        adm_print (" -> not useable")
        return
    # get the permissions and plugins first, since that might change possible candidates for manifest and config
    permissions = aa.get_permissions();
    plugins = aa.get_plugins();
    aa.find_index()
    aa.find_cordova()
    aa.find_jQuery()
    out.write(dir+";")
    out.write(aa.get_pg_version()+";")
    out.write(aa.index_html_abs+";")
    out.write(str(aa.cordova_abs)+";")
    out.write(str(aa.jquery_abs)+";")
    out.write(str(permissions)+";")
    out.write(str(len(permissions))+";")
    out.write(str(plugins)+";")
    out.write(str(len(plugins))+";")
    buttons = aa.get_buttons()
    out.write(str(aa.get_buttons())+";")
    out.write(str(len(buttons))+";")
    out.write("\n")

def is_useable(aa):
    if (aa.find_config()==1): # If the config was not found -> no idea about the plugins. Therefore not useable
        return False
    if (aa.find_index()!=0): # Need exactly one main html to policify
        return False
    if (aa.find_cordova()==1): # need to policify each cordova library, to catch the ondeviceready handlers, if it is not found, no policification possible
        return False
    return True
    
    
def analyse(dir):
    global csv_output
    if (csv_output):
        analyse_csv(dir)
    else :
        analyse_humanReadable(dir)
    
#globale optionen
interactive = False
csv_output = False
filter_useable = False
quite = False
out = sys.stdout
    
def is_option(arg):
    return (arg[0] == "-")
    
def read_options(args):
    global interactive
    global csv_output
    global filter_useable
    global quite
    global out
    arg_next = 1
    while (len(args)>arg_next) and (is_option(args[arg_next])):
        if (args[arg_next] == "-i"): # interactive: ask for confirmation, if there are multiple candidate files
            interactive = (True and (not quite))
        elif (args[arg_next] == "-csv"): # output results as comma separated values. Values are seperated with ; and lines with \n
            csv_output = True
        elif (args[arg_next] == "-f"): # only output those that can be policified
            filter_useable = True
        elif (args[arg_next] == "-q"): # Don't print out administrative messages -> implies !interactive
            quite = True
            interactive = False
        elif (args[arg_next] == "-o"): # route output to a file
            arg_next = arg_next + 1
            if ( (len(args) == arg_next) or (is_option(args[arg_next])) ):
                 adm_print("Specify file name after -o")
                 exit(1)
            out = open(args[arg_next],"a")
        arg_next = arg_next + 1
    return arg_next
        
    
def main():
    fid = read_options(sys.argv)
    if (len(sys.argv)>fid):
        adm_print("analysing " + sys.argv[fid])
        analyse(sys.argv[fid])
    else :
        adm_print("analysing working directory")
        analyse(".")

if __name__ == "__main__":
    main()

