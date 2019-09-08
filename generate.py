#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys
import subprocess
import json
import tempfile
from shutil import copyfile
from shutil import rmtree
from subprocess import run, PIPE

REMOTE_DATABASE = "https://raw.githubusercontent.com/qxcodefup/arcade/master/base"

BASE    = "base"
PROF    = "a_prof"
STUDENT = "a_student"
MOODLE  = "a_moodle"


def extract_index_name(target_dir):
    with open(target_dir + os.sep + "Readme.md") as f:
        words = f.readlines()[0].split(" ")
        index = words[1][1:] #primeira palavra, retirando o @
        name = " ".join(words[1:]) #retirando apenas o ##
        return [index, name]

def replace_references_on_figures(text, remote_server):
    return text.replace('<img src="__', '<img src="' + remote_server + "/" + "__")

def generate_json(hook, name, description, cases, fdict):
    moodle = {}
    moodle["name"] = name
    moodle["description"] = description
    moodle["executionFiles"] = [{"name":"vpl_evaluate.cases", "contents": cases}]

    files = fdict["vpls"] + fdict["others"]

    for file in files:
        with open(BASE + os.sep + hook + os.sep + file) as f:
            moodle["executionFiles"].append({"name": file, "contents": f.read()})

    for file in fdict["solvers"]:
        with open(BASE + os.sep + hook + os.sep + file) as f:
            moodle["executionFiles"].append({"name": file + ".txt", "contents": f.read()})


    if len(fdict["required"]) == 0:
        moodle["requiredFile"] = None
    else:
        required = fdict["required"][0]
        with open(BASE + os.sep + hook + os.sep + required) as f:
            moodle["requiredFile"] = {"name": required, "contents": f.read()}

    return json.dumps(moodle, indent = 2)

def make_file_dict(hook):
    files = os.listdir(BASE + os.sep + hook)
    files.remove("Readme.md")
    files   = [x for x in files if os.path.isfile(BASE + os.sep + hook + os.sep + x)] #filtering directories
    files   = [x for x in files if (x.find(".") != -1)]    #filtering executables
    files   = [x for x in files if not x.endswith(".exe")] #filtering executables

    tests   = [x for x in files if x.endswith(".tio")]
    files   = [x for x in files if x not in tests] #filtering tests
    
    figs    = [x for x in files if (x.endswith(".png") or x.endswith(".jpg") or x.endswith(".jpeg") or x.endswith(".gif"))]
    files   = [x for x in files if x not in figs] #filtering figs

    solvers = [x for x in files if x.startswith("solver")]
    files   = [x for x in files if x not in solvers]

    vpls    = [x for x in files if x.startswith("vpl_")]
    files   = [x for x in files if x not in vpls]

    required = [x for x in files if x.startswith("student")]
    files   = [x for x in files if x not in required]

    files   = [x for x in files if not x.startswith("__")] #filtering ignored files
    others  = files

    fdict = {}
    fdict["figs"]     = [x for x in figs]
    fdict["vpls"]     = [x for x in vpls]
    fdict["solvers"]  = [x for x in solvers]
    fdict["required"] = [x for x in required]
    fdict["others"]   = [x for x in others]
    fdict["tests"]    = [x for x in tests]
    return fdict

def update_student(hook, name, cases_tio, description, fdict):
    dest = STUDENT + os.sep + hook
    rmtree(dest, ignore_errors=True)
    os.mkdir(dest)
    with open(dest + os.sep + "s.html", 'w') as f:
        f.write(description)
    with open(dest + os.sep + "s.tio", 'w') as f:
        f.write(cases_tio)
    files = fdict["others"] + fdict["figs"] + fdict["required"]
    for f in files:
        copyfile(BASE + os.sep + hook + os.sep + f, dest + os.sep + f)

def update_prof(hook, name, cases_vpl, description_filtered, fdict):
    dest = PROF + os.sep + hook
    rmtree(dest, ignore_errors=True)
    os.mkdir(dest)
    with open(dest + os.sep + "p.html", 'w') as f:
        f.write(description_filtered)
    with open(dest + os.sep + "p.vpl", 'w') as f:
        f.write(cases_vpl)
    files = fdict["others"] + fdict["required"] + fdict["vpls"] + fdict["solvers"]
    for f in files:
        copyfile(BASE + os.sep + hook + os.sep + f, dest + os.sep + f)


def update_all(hook):
    print("making", hook)
    [index, name] = extract_index_name(BASE + os.sep + hook)
    pathReadme = BASE + os.sep + hook + os.sep + "Readme.md"
    
    description = generate_html(name, pathReadme)
    description_filtered = replace_references_on_figures(description, REMOTE_DATABASE + os.sep + index)

    fdict = make_file_dict(hook)

    cases_vpl = generate_cases([pathReadme] + fdict["tests"], ".vpl")
    cases_tio = generate_cases([pathReadme] + fdict["tests"], ".tio")

    moodle = generate_json(hook, name, description_filtered, cases_vpl, fdict)
    with open(MOODLE + os.sep + hook + ".json", "w") as f:
        f.write(moodle)

    update_student(hook, name, cases_tio, description, fdict)
    update_prof(hook, name, cases_vpl, description_filtered, fdict)
    
    
def generate_cases(infiles, extension):
    tempDir = tempfile.TemporaryDirectory()
    outfile = tempDir.name + os.sep + "t" + extension
    cmd = ["th", "build", outfile]
    for infile in infiles:
        if os.path.isfile(infile):
            cmd.append(infile)
    cmd.append("-q")
    try:
        p = subprocess.Popen(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        stdout, stderr = p.communicate()
        if(stdout != "" or stderr != ""):
            print(stdout)
            print(stderr)
        with open(outfile) as f:
            return f.read()
    except Exception as e:
        print("Erro no comando th:", e)
        exit(1)


"""
generate a html page from infile
if remote_server not null, all reference to images begining with __
will be updates to full url
"""
def generate_html(title, infile):
    tempDir = tempfile.TemporaryDirectory()
    outfile = tempDir.name + os.sep + "t.html"

    fulltitle = title.replace('!', '\\!').replace('?', '\\?')
    cmd = ["pandoc", infile, '--metadata', 'pagetitle=' + fulltitle, '-s',  '-o', outfile]
    try:
        p = subprocess.Popen(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        stdout, stderr = p.communicate()
        if(stdout != "" or stderr != ""):
            print(stdout)
            print(stderr)
        with open(outfile) as f:
            return f.read()
    except Exception as e:
        print("Erro no comando pandoc:", e)
        exit(1)

def main():
    files = os.listdir(BASE)
    
    folders = [x for x in files if os.path.isdir(BASE + os.sep + x)]
    for f in folders:
        source = BASE + os.sep + f + os.sep + "Readme.md"
        target = MOODLE + os.sep + f + ".json"
        if not os.path.exists(target) or (os.path.getmtime(source) > os.path.getmtime(target)):
            update_all(f)

if __name__ == '__main__':
    main()