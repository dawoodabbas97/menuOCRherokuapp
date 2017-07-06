# -*- coding: utf-8 -*-
#Code developed by A.Dawood Abbas @T2S
import os
import os.path
import subprocess
import sys
import json
import re
import logging
from json import dumps, load
import shutil
from flask import Flask, jsonify, render_template, request, send_from_directory,send_file
from werkzeug import secure_filename

app = Flask(__name__)
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.ERROR)
app.config['PROPAGATE_EXCEPTIONS'] = True
app.config['TEMP_FOLDER'] = '/tmp'
app.config['OCR_OUTPUT_FILE'] = 'ocr'
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in set(['png', 'jpg', 'jpeg', 'gif', 'tif', 'tiff'])

@app.errorhandler(404)
def not_found(error):
    resp = jsonify( { 
        u'status': 404, 
        u'message': u'Resource not found' 
    } )
    resp.status_code = 404
    return resp

@app.route('/')
def api_root():
    resp = jsonify( { 
        u'status': 200, 
        u'message': u'Welcome to RestaurantMenuOCR redirect to /test' 
    } )
    resp.status_code = 200
    return resp

@app.route('/test', methods = ['GET'])
def test():
    
    return render_template('upload_form.html', landing_page = 'process')

@app.route('/process', methods = ['GET','POST'])
def process():

   
    if request.method == 'POST':

           
        file = request.files['file']
        
        #hocr = request.form.get('hocr') or ''
        #ext = '.hocr' if hocr else '.txt'
        ext='.txt'
        if file and allowed_file(file.filename):
            if not os.path.exists(os.path.join(app.config['TEMP_FOLDER'],str(os.getpid()))):
                folder = os.path.join(app.config['TEMP_FOLDER'], str(os.getpid()))
            else:
                shutil.rmtree(os.path.join(app.config['TEMP_FOLDER'], str(os.getpid())))
                #os.remove(os.path.join(app.config['TEMP_FOLDER'],str(os.getpid())))
                folder = os.path.join(app.config['TEMP_FOLDER'], str(os.getpid()))
            os.mkdir(folder)
            input_file = os.path.join(folder, secure_filename(file.filename))
            output_file = os.path.join(folder, app.config['OCR_OUTPUT_FILE'])
            file.save(input_file)
            
            command = ['tesseract', input_file, output_file, '-l']
            proc = subprocess.Popen(command, stderr=subprocess.PIPE)
            proc.wait()
            
            output_file += ext
            
            if os.path.isfile(output_file):
                f = open(output_file)
                for v in enumerate(f.read().splitlines()):
                    with open( os.path.join(folder,"a.txt"),"a") as g:
                        g.write(str(v[1])+"\n") 
                #return send_from_directory(os.path.join(app.config['TEMP_FOLDER']),"a.txt")
                extractMenu()
                return send_file(folder+"/a.json", as_attachment=True, attachment_filename="output.json")


                
    #             resp = jsonify( {
    #                 u'status': 200,
    #                 u'ocr':{k:v for k,v in enumerate(f.read().splitlines())}
    #             } )
            else:
                resp = jsonify( {
                    u'status': 422,
                    u'message': u'Unprocessable Entity'
                } )
                resp.status_code = 422
            
            shutil.rmtree(folder)
            return resp
        else:
            resp = jsonify( { 
                u'status': 415,
                u'message': u'Unsupported Media Type' 
            } )
            resp.status_code = 415
            return resp
    else:
        resp = jsonify( { 
            u'status': 405, 
            u'message': u'The method is not allowed for the requested URL' 
        } )
        resp.status_code = 405
        return resp

def extractMenu():
    head=""
    headings=[]
    menu={}
    unrecogonised=[]
    done="false"
    menu["headings"]={}     
    categories = ['Extra Toppings','Calzone','biryanidishes','vegetabledishes','sundries','dips','rice','westerndishes','freshlybakedpizza' ,'starters','burgers','kebabselection','sideorders','bakedpotatoes','westerndishes','classicsideorders','premiumsideorders','burgers','desserts','drinks','kidsmeals',"pizzas","tandoorisundries","quicksnacks","tandooridishes"];
    cat=""
    for s in categories:
        cat+=s.lower().replace(" ","")+" "
    with open(os.path.join(app.config['TEMP_FOLDER'], str(os.getpid()))+"/a.txt","r") as f:
        flag=0;
        recogonised=1
        for line in f:
            for word in line.split("\n"):
                
                if u"£" in word and word and not word.isspace():
                    flag=0
                    item={}
                    recogonised=1
                    if word.count(u"£")>=2:
                    
                        dish=re.search( r'(([a-zA-Z0-9\s\&\@\!]+))', word, re.M|re.I)
                        item["name"]=dish.group()
                    
                        price=re.findall( r'£[0-9]*.\d+', word.replace(" ",""), re.M|re.I)
                      
                        pcat=0
                        for p in price:
                            pcat+=1
                        
                            item["price_"+str(pcat)]=p.strip(u"£")
                    
                        if head=="" or recogonised==0:
                            head="start"
                            menu["headings"][head]={}
                            menu["headings"][head]["items"]=[]
                            menu["headings"][head]["items"].append(item)
                
                        else:
                            menu["headings"][head]["items"].append(item)
                    else:
                        price=re.search( r'((£\d\.\d+)+|(£\d+))', word, re.M|re.I).group()
                        dish=re.search( r'(([a-zA-Z0-9\s\&]+))', word, re.M|re.I).group()
                        item["name"]=dish
                        item["price"]=price.strip(u"£")
                
                        if head=="" or recogonised==0:
                            head="start"
                            menu["headings"][head]={}
                            menu["headings"][head]["items"]=[]
                            menu["headings"][head]["items"].append(item)
                
                        else:
                            menu["headings"][head]["items"].append(item)
                elif word.lower().replace(" ","") in cat and  word and not word.isspace():
                    flag=1
                    
                    recogonised=1
                    menu["headings"][word]={}
                    menu["headings"][word]["items"]=[]
                    head=word

                elif flag==0 and word and not word.isspace():
                
                    recogonised=1
                    if head=="":
                        head=word
                        menu["headings"][head]={}
                        menu["headings"][head]["items"]=[]
                    elif menu["headings"][head]["items"] and "description" in  menu["headings"][head]["items"][-1] :
                        menu["headings"][head]["items"][-1]["description"]+=word+" "

                    elif menu["headings"][head]["items"]:
                        menu["headings"][head]["items"][-1]["description"]=word
                        
                
                elif flag==1 and word and not word.isspace():
                    recogonised=1
                    
                    if "Regular" and "Large" not in word:
                        if "description" in menu["headings"][head]:
                            menu["headings"][head]["description"]+=word+" "
                        else:
                            menu["headings"][head]["description"]=word
                else:
                    
                    recogonised=0
                    if word and not word.isspace():
                        unrecogonised.append(word)
            
                    

                
    menu["unrecogonised"]=[]
    menu["unrecogonised"]=unrecogonised
    
    with open(os.path.join(app.config['TEMP_FOLDER'], str(os.getpid()))+"/a.json","w") as f:
        f.write(dumps(menu,sort_keys=True, indent=4))

if __name__ == '__main__':
    app.run(debug=True)
