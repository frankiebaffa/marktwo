# TODO: Add ability to set classes in content block
#       example: &> ((.tl-fixed)) /> *> !> this is a table cell <!<*</<&

import re
import sys
from models.marktwoelement import MarkTwoElement
from utils.utils import arrFind, regexHas, regexHasOne
from marktwoerrors import MarkTwoParseError, MarkTwoFileNotFoundError

class MarkTwoParser:
    def __init__(self,options=None,testinput=None):
        self.options = options
        self.allClasses = []
        self.qdocument = MarkTwoElement()
        self.qdocument.qtag = "document"
        self.qdocument.qid  = "Document"
        self.hdocument = MarkTwoElement()
        self.hdocument.qtag = "document"
        self.hdocument.qid  = "Document"
        self.fdocument = MarkTwoElement()
        self.fdocument.qtag = "document"
        self.fdocument.qid  = "Document"
        self.html = ''
        self.headhtml = ''
        self.foothtml = ''
        self.lvars = MarkTwoParser._getDefaultLayoutVars()
        self.content = {}
        self.headcontent = {}
        self.footcontent = {}
        self.overrides = {
                "page-size":None,
                "margin-top":None,
                "margin-right":None,
                "margin-bottom":None,
                "margin-left":None,
                "font-scale":None
                }
        self.constants = {
                "indent":None
                }

        startpass = False
        if options['singlefile'] != None:
            try:
                with open(options['singlefile'],'r') as file:
                    doctxt = file.read()
                    self.qinput = doctxt
                    startpass = True
            except FileNotFoundError as e:
                raise MarkTwoFileNotFoundError(
                        parent=e,
                        specific_message="Could not find specified input file."
                        )
        if options['test'] and testinput != None:
            self.qinput = testinput
            startpass = True

        if startpass:
            arr = self.qinput.split('\n')

            # remove comments from array
            for i in range(len(arr)):
                line = arr[i]
                try:
                    indexofcomment = line.index("!#")
                    line = line[0:indexofcomment]
                    line = re.sub(r"\s*$","",line)
                    arr[i] = line
                except:
                    pass

            arr = self.pullHeader(arr)
            arr = self.pullFooter(arr)
            self.getConf(arr)
            self.getLayoutVars(arr)
            self._parse(arr)
            self.getStyle(arr)
            self.getScript(arr)
            if self.headarr != None:
                self._parse(self.headarr,loc="header")
            if self.footarr != None:
                self._parse(self.footarr,loc="footer")
            if self.css != None:
                self._appendStyle()
            if self.script != None:
                self._appendScripts()

    @staticmethod
    def _blockStartEnd(s:int, e:int, b:str, quiet=False) -> bool:
        started         = s > -1
        ended           = e > -1
        placementproper = s < e
        if started and ended and placementproper:
            return True
        elif started and not ended:
            raise MarkTwoParseError(
                    specific_message=f"{b} is an unclosed block."
                    )
        elif not started and ended:
            raise MarkTwoParseError(
                    specific_message=f"{b} is never started and attempted closing."
                    )
        elif started and ended and not placementproper:
            raise MarkTwoParseError(
                    specific_message=f"{b} is improperly defined."
                    )
        elif not started and not ended:
            if not quiet: print(f"{b} not defined.")
            return False
        else:
            raise MarkTwoParseError(
                    specific_message=f"{b} contains a questionable section."
                    )

    def _parse(self, arr:list, loc=None) -> None:
        self.getContent(arr,loc=loc)
        self.getLayout(arr,loc=loc)

    def _appendStyle(self) -> None:
        self.html     += f"\n<style>\n{self.css}\n</style>"
        self.headhtml += f"\n<style>\n{self.css}\n</style>"
        self.foothtml += f"\n<style>\n{self.css}\n</style>"

    def _getStyleClasses(self) -> str:
        pxorauto = r"([0-9]+|auto)"
        # (full pattern, value pattern, css string)
        stylesbypixel = [
                (r"m-"+pxorauto, pxorauto, "margin:$;"),
                (r"p-"+pxorauto, pxorauto, "padding:$;"),
                (r"mx-"+pxorauto, pxorauto, "margin-left:$;margin-right:$;"),
                (r"my-"+pxorauto, pxorauto, "margin-top:$;margin-bottom:$;"),
                (r"px-"+pxorauto, pxorauto, "padding-left:$;padding-right:$;"),
                (r"py-"+pxorauto, pxorauto, "padding-top:$;padding-bottom:$;"),
                (r"mb-"+pxorauto, pxorauto, "margin-bottom:$;"),
                (r"mt-"+pxorauto, pxorauto, "margin-top:$;"),
                (r"ml-"+pxorauto, pxorauto, "margin-left:$;"),
                (r"mr-"+pxorauto, pxorauto, "margin-right:$;"),
                (r"pb-"+pxorauto, pxorauto, "padding-bottom:$;"),
                (r"pt-"+pxorauto, pxorauto, "padding-top:$;"),
                (r"pl-"+pxorauto, pxorauto, "padding-left:$;"),
                (r"pr-"+pxorauto, pxorauto, "padding-right:$;"),
                ]
        stylesbypercent = [
                (r"w-"+pxorauto, pxorauto, "width:$;"),
                (r"h-"+pxorauto, pxorauto, "height:$;"),
                ]
        textmods = r"(left|center|right)"
        textaligns = [
                (r"text-"+textmods, textmods, "text-align:$;")
                ]
        tablemods = r"(fixed|auto|initial|inherit)"
        tablelayouts = [
                (r"tl-"+tablemods, tablemods, "table-layout:$;")
                ]

        stylesbypixelvalues = r"-([0-9]+|auto)"
        stylesbypercentvalues = r"-[0-9]+"
        textvalues = r"-(left|center|right)"

        allCss = []
        for clas in self.allClasses:
            for style in stylesbypixel:
                if (search := re.search(style[0], clas)) != None:
                    if (valsearch := re.search(style[1], search.group())) != None:
                        val = valsearch.group()
                        css = "."+search.group()+"{"+style[2]+"}"
                        if val != "auto":
                            css = re.sub(r"\$", val+"px", css)
                        else:
                            css = re.sub(r"\$", val, css)
                        if not css in allCss:
                            allCss.append(css)

        for clas in self.allClasses:
            for style in stylesbypercent:
                if (search := re.search(style[0], clas)) != None:
                    if (valsearch := re.search(style[1], search.group())) != None:
                        val = valsearch.group()
                        css = "."+search.group()+"{"+style[2]+"}"
                        if val != "auto":
                            css = re.sub(r"\$", val+"%", css)
                        else:
                            css = re.sub(r"\$", val, css)
                        if not css in allCss:
                            allCss.append(css)

        for clas in self.allClasses:
            for style in textaligns:
                if (search := re.search(style[0], clas)) != None:
                    if (valsearch := re.search(style[1], search.group())) != None:
                        val = valsearch.group()
                        css = "."+search.group()+"{"+style[2]+"}"
                        css = re.sub(r"\$", val, css)
                        if not css in allCss:
                            allCss.append(css)

        for clas in self.allClasses:
            for style in tablelayouts:
                if (search := re.search(style[0], clas)) != None:
                    if (valsearch := re.search(style[1], search.group())) != None:
                        val = valsearch.group()
                        css = "."+search.group()+"{"+style[2]+"}"
                        css = re.sub(r"\$", val, css)
                        if not css in allCss:
                            allCss.append(css)

        css = "".join([str(x) for x in allCss])

        return css

    def _getDefaultStyle(self) -> None:
        self.css += ""+\
            "h1,h2,h3,h4,h5,h6{color:grey;font-weight:bold;font-style:normal;}"+\
            "p,span,pre,code,td,ul,"+\
            "tr,li,ul,a,sub,sup{color:black;font-weight:normal;font-style:normal;}"+\
            "*{margin-top:0px;margin-bottom:0px;padding-top:0px;padding-bottom:0px}"+\
            "hr,sup,sub{line-height:0;}"+\
            "table{table-layout:fixed;width:100%;}"+\
            "td{vertical-align:top;}"+\
            "pre,code,a{font-size:inherit;}"+\
            "table>tbody>tr>td{width:100%;}"
        fontoverrides = {
                "sm": ""+\
                    "h1{font-size:20px;}"+\
                    "h2{font-size:18px;}"+\
                    "h3{font-size:16px;}"+\
                    "h4{font-size:14px;}"+\
                    "h5{font-size:12px;}"+\
                    "h6{font-size:10px;}"+\
                    "p,span,li,td{font-size:10px;}",
                "rg": ""+\
                    "h1{font-size:22px;}"+\
                    "h2{font-size:20px;}"+\
                    "h3{font-size:18px;}"+\
                    "h4{font-size:16px;}"+\
                    "h5{font-size:14px;}"+\
                    "h6{font-size:12px;}"+\
                    "p,span,li,td{font-size:12px;}",
                "lg": ""+\
                    "h1{font-size:24px;}"+\
                    "h2{font-size:22px;}"+\
                    "h3{font-size:20px;}"+\
                    "h4{font-size:18px;}"+\
                    "h5{font-size:16px;}"+\
                    "h6{font-size:14px;}"+\
                    "p,span,li,td{font-size:14px;}",
                }
        if (fontscale := self.overrides["font-scale"]) != None:
            self.css += fontoverrides[fontscale]
        else:
            self.css += fontoverrides["rg"]

    def _appendScripts(self) -> None:
        self.html     += f"\n<script>\n{self.script}\n</script>"
        self.headhtml += f"\n<script>\n{self.script}\n</script>"
        self.foothtml += f"\n<script>\n{self.script}\n</script>"

    @staticmethod
    def _getDefaultLayoutVars() -> dict:
        return {
                 # THREE INLINE TEXT ELEMENTS ALIGNED LEFT, CENTER, RIGHT; RESPECTIVELY
                 "lcr":[
                        "<table style='width:100%;table-layout:fixed;' class='lcrContainer'>",
                        "<tbody>",
                        "<tr>",
                        "<td id style='width:50%;text-align:left;'></td>",
                        "<td id style='width:50%;text-align:center;'></td>",
                        "<td id style='width:50%;text-align:right;'></td>",
                        "</tr>",
                        "</tbody>",
                        "</table>"
                       ],
                 # TWO INLINE TEXT ELEMENTS ALIGNED LEFT, RIGHT; RESPECTIVELY
                 "lr": [
                        "<table style='width:100%;table-layout:fixed;' class='lrContainer'>",
                        "<tbody>",
                        "<tr>",
                        "<td id style='width:50%;text-align:left;'></td>",
                        "<td id style='width:50%;text-align:right;'></td>",
                        "</tr>",
                        "</tbody>",
                        "</table>"
                       ]
                }

    def pullHeader(self, arr:list) -> list:
        self.headarr = None
        contentstart = arrFind('<!HEADCONTENT>',arr)
        contentend   = arrFind('<!/HEADCONTENT>',arr)
        has = MarkTwoParser._blockStartEnd(contentstart,contentend,"Content Block (header)",quiet=True)
        if has:
            newarr = ['<!CONTENT>']
            for i in range(contentstart+1,contentend):
                newarr.append(arr[i])
            newarr.append('<!/CONTENT>')
            arr = arr[0:contentstart]+arr[contentend+1:len(arr)]

        layoutstart = arrFind('<!HEADLAYOUT>',arr)
        layoutend   = arrFind('<!/HEADLAYOUT>',arr)
        has = MarkTwoParser._blockStartEnd(layoutstart,layoutend,"Layout Block (header)",quiet=True)
        if has:
            newarr.append('<!LAYOUT>')
            for i in range(layoutstart+1,layoutend):
                newarr.append(arr[i])
            newarr.append('<!/LAYOUT>')
            arr = arr[0:layoutstart]+arr[layoutend+1:len(arr)]
            self.headarr = newarr

        return arr

    def pullFooter(self, arr:list) -> list:
        self.footarr = None
        contentstart = arrFind('<!FOOTCONTENT>',arr)
        contentend   = arrFind('<!/FOOTCONTENT>',arr)
        has = MarkTwoParser._blockStartEnd(contentstart,contentend,"Content Block (footer)",quiet=True)
        if has:
            newarr = ['<!CONTENT>']
            for i in range(contentstart+1,contentend):
                newarr.append(arr[i])
            newarr.append('<!/CONTENT>')
            arr = arr[0:contentstart]+arr[contentend+1:len(arr)]

        layoutstart = arrFind('<!FOOTLAYOUT>',arr)
        layoutend   = arrFind('<!/FOOTLAYOUT>',arr)
        has = MarkTwoParser._blockStartEnd(layoutstart,layoutend,"Layout Block (footer)",quiet=True)
        if has:
            newarr.append('<!LAYOUT>')
            for i in range(layoutstart+1,layoutend):
                newarr.append(arr[i])
            newarr.append('<!/LAYOUT>')
            arr = arr[0:layoutstart]+arr[layoutend+1:len(arr)]
            self.footarr = newarr

        return arr

    def getConf(self, arr:list) -> None:
        confstart = arrFind('<!CONF>',arr)
        confend   = arrFind('<!/CONF>',arr)
        has = MarkTwoParser._blockStartEnd(confstart,confend,"Configuration Block")
        if has:
            for i in range(confstart+1,confend):
                line = arr[i].lstrip().rstrip()
                key  = re.findall(r"\S+(?==)",line)
                val  = re.findall(r"(?<==)\S+",line)
                if len(key) > 0 and len(val) > 0:
                    try:
                        self.overrides[key[0]]
                        self.overrides[key[0]] = val[0]
                    except:
                        try:
                            self.constants[key[0]]
                            self.constants[key[0]] = val[0]
                        except:
                            print(f"Invalid configuration option: '{key[0]}'.")

    def getContent(self, arr:list, loc=None) -> None:
        locstr = None
        if loc == None: locstr = "main"
        else: locstr = loc
        contentstart  = arrFind('<!CONTENT>',arr)
        contentend    = arrFind('<!/CONTENT>',arr)
        has = MarkTwoParser._blockStartEnd(contentstart,contentend,f"Content Block ({locstr})")
        if has:
            previousId    = None
            contentconcat = ''
            for i in range(contentstart+1,contentend):
                #line = re.sub(r"^[\s\t]+","",arr[i],1)
                line = arr[i].lstrip().rstrip()
                if line[0:1] == '#':
                    kv            =  re.split(r":",line)
                    kv[1]         =  kv[1].lstrip()
                    cid           =  kv[0][1:len(kv[0])]
                    contentconcat += kv[1]
                    previousId    =  cid
                else:
                    contentconcat += f" {line}"
                if i == contentend-1 or arr[i+1].lstrip().rstrip()[0:1] == '#':
                    if contentconcat != None and contentconcat != '':
                        if loc == None:
                            contentconcat = MarkTwoParser.checkContentForInline(contentconcat)
                            contentconcat = self.checkContentForVars(contentconcat)
                            self.content[previousId] = contentconcat
                        elif loc == "header":
                            contentconcat = MarkTwoParser.checkContentForInline(contentconcat)
                            contentconcat = self.checkContentForVars(contentconcat)
                            self.headcontent[previousId] = contentconcat
                        elif loc == "footer":
                            contentconcat = MarkTwoParser.checkContentForInline(contentconcat)
                            contentconcat = self.checkContentForVars(contentconcat)
                            self.footcontent[previousId] = contentconcat
                        contentconcat =  ''

            # HOTFIX FOR UNECESSARY SPACES BETWEEN EMPTY TAGS
            if loc == None:
                for key in self.content.keys():
                    block    = self.content[key]
                    patt     = r"(?<!\s)\>\s\<"
                    block    = re.sub(patt,"><",block)
                    self.content[key] = block
            if loc == "header":
                for key in self.headcontent.keys():
                    block    = self.headcontent[key]
                    patt     = r"(?<!\s)\>\s\<"
                    block    = re.sub(patt,"><",block)
                    self.headcontent[key] = block
            if loc == "footer":
                for key in self.footcontent.keys():
                    block    = self.footcontent[key]
                    patt     = r"(?<!\s)\>\s\<"
                    block    = re.sub(patt,"><",block)
                    self.footcontent[key] = block

            # HOTFIX FOR UNECESSARY SPACES AFTER TEXT IN TAG
            if loc == None:
                for key in self.content.keys():
                    block = None
                    block = self.content[key]
                    patt  = r"(?<=\S)\s(?=$)"
                    matchobj = [(m.start(0),m.end(0)) for m in re.finditer(patt,block)]
                    newblock = None
                    if len(matchobj) > 0:
                        match    = matchobj[0]
                        newblock = block[0:match[0]]
                        self.content[key] = newblock
            elif loc == "header":
                for key in self.headcontent.keys():
                    block = None
                    block = self.headcontent[key]
                    patt  = r"(?<=\S)\s(?=$)"
                    matchobj = [(m.start(0),m.end(0)) for m in re.finditer(patt,block)]
                    newblock = None
                    if len(matchobj) > 0:
                        match    = matchobj[0]
                        newblock = block[0:match[0]]
                        self.headcontent[key] = newblock
            if loc == "footer":
                for key in self.footcontent.keys():
                    block = None
                    block = self.footcontent[key]
                    patt  = r"(?<=\S)\s(?=$)"
                    matchobj = [(m.start(0),m.end(0)) for m in re.finditer(patt,block)]
                    newblock = None
                    if len(matchobj) > 0:
                        match    = matchobj[0]
                        newblock = block[0:match[0]]
                        self.footcontent[key] = newblock

    @staticmethod
    def checkContentForLiteral(text:str) -> str:
        getliteralsections   = r"(?<!\\){{.*?(?<!\\)}}"
        literalsections      = re.findall(getliteralsections,text)
        getcharstoliteralize = r"[^a-zA-Z0-9\s\t\n\.,]"
        for literalsection in literalsections:
            if literalsection.find("{{") == 0 and literalsection.rfind("}}") == len(literalsection)-2:
                newliteralsection = f"{literalsection[2:len(literalsection)-2]}"
                charstoliteralize = re.findall(getcharstoliteralize,newliteralsection)
                charstoliteralize = list(set(charstoliteralize))
                for char in charstoliteralize:
                    newliteralsection = newliteralsection.replace(char, f"\\{char}")
                newliteralsection = newliteralsection.rstrip().lstrip()
                text = text.replace(literalsection, newliteralsection)
        return text

    @staticmethod
    def checkContentForInline(text:str) -> str:
        try:
            openclose = {
                    r"(?<!\\)_"          : "em",
                    r"(?<!\\)\*"         : "strong",
                    r"(?<![\\\-])-(?!-)" : "s",
                    r"(?<![\\])\|"       : "li",
                    r"(?<![\\])\^"       : "sup",
                    r"(?<![\\])\~"       : "sub"
                    }

            opendiffclose = {
                             "ul" : {
                                    "open"  : r"(?<![\\])\%\>",
                                    "close" : r"(?<![\\])\<\%"
                                },
                             "ol" : {
                                    "open"  : r"(?<![\\])\$\>",
                                    "close" : r"(?<![\\])\<\$"
                                },
                             "table" : {
                                    "open"  : r"(?<![\\])\&\>",
                                    "close" : r"(?<![\\])\<\&"
                                },
                             "tbody" : {
                                    "open"  : r"(?<![\\])\/\>",
                                    "close" : r"(?<![\\])\<\/"
                                },
                             "tr" : {
                                    "open"  : r"(?<![\\])\*\>",
                                    "close" : r"(?<![\\])\<\*"
                                },
                             "td" : {
                                    "open"  : r"(?<![\\])\!\>",
                                    "close" : r"(?<![\\])\<\!"
                                },
                            }

            standalone = {r"(?<!\\)[\s]*\-\-[\s]*" : "br"} # space due to how content processes
            linktextpat = r"(?<=\[).+(?=\])"
            linkpat = r"(?<=\().+(?=\))"

            text = MarkTwoParser.checkContentForLiteral(text)

            for tagname in opendiffclose.keys():
                openpat = opendiffclose[tagname]["open"]
                clospat = opendiffclose[tagname]["close"]
                text    = re.sub(openpat,f"\\<{tagname}\\>",text)
                text    = re.sub(clospat,f"\\</{tagname}\\>",text)

            for key in openclose.keys():
                matches = re.findall(key,text)
                count   = len(matches)
                evenodd = count%2
                for i in range(count-evenodd):
                    if i%2 == 0:
                        text = re.sub(key,f"<{openclose[key]}>",text,1)
                    elif i%2 == 1:
                        text = re.sub(key,f"</{openclose[key]}>",text,1)

            for key in standalone.keys():
                matches = re.findall(key,text)
                text = re.sub(key,f"<{standalone[key]}>",text)

            matchobj    = [(m.start(0),m.end(0)) for m in re.finditer(linktextpat,text)]
            match       = matchobj[0]
            linkstr     = text[match[0]:match[1]]
            removestr   = r"\["+linkstr+"\]"
            matchobj    = [(m.start(0),m.end(0)) for m in re.finditer(linkpat,text)]
            match       = matchobj[0]
            linkhyper   = text[match[0]:match[1]]
            text        = text.replace('=','\\=').replace('/','\\/').replace('?','\\?')
            linkhyper   = linkhyper.replace('=','\\=').replace('/','\\/').replace('?','\\?')
            if linkstr not in (None,'') and linkhyper not in (None,''):
                text = re.sub(removestr,f"<a href=\"{linkhyper}\">{linkstr}</a>",text)
                text = re.sub(r"\([a-zA-Z0-9\.\\\/\:\&\?]+\)","",text)
        except:
            pass

        text = text.replace("\\","")
        return text

    def checkContentForVars(self, content:str) -> str:
        def wrapVar(p):
            return r"(?<!\\)@"+p+r"(?<!\\)@"

        contentvars = [
                        {
                            "name"       :"pagebreak",
                            "pattern"    :wrapVar(r"pagebreak"),
                            "replacement":"<div style='page-break-before:always;display:block;width:0px;height:0px;'></div>"
                        }
                      ]
        dynamicvars = [
                        {
                            "name"       :r"indent",
                            "modpattern" :r"(?<=indent)[0-9]+",
                            "pattern"    :wrapVar(r"indent[0-9]+"),
                            "modifier"   :"width",
                            "replacement":"<span style='display:inline-block;margin:0px;padding:0px;width:{width}px;'></span>"
                        }
                      ]
        for var in contentvars:
            content = re.sub(var["pattern"],var["replacement"],content)

        for var in dynamicvars:
            pat       = var["pattern"]
            foundvars = re.findall(pat,content)
            for dynvar in foundvars:
                mod = re.findall(var["modpattern"],dynvar)[0]
                replacement = re.sub(r"{"+var["modifier"]+"}",mod,var["replacement"])
                content = re.sub(dynvar,replacement,content)

        for var in dynamicvars:
            pat       = wrapVar(var["name"])
            foundvars = re.findall(pat,content)
            for convar in foundvars:
                if self.constants[var["name"]] != None:
                    mod = self.constants[var["name"]]
                    replacement = re.sub(r"{"+var["modifier"]+"}",mod,var["replacement"])
                    content = re.sub(convar,replacement,content)
                else:
                    print("Instance of constant variable without declaration of constant")
        return content

    def getLayoutVars(self, arr:list) -> None:
        lvarstart = arrFind('<!LAYOUTVARS>',arr)
        lvarend   = arrFind('<!/LAYOUTVARS>',arr)
        has = MarkTwoParser._blockStartEnd(lvarstart,lvarend,"Layout Variable Block")
        if has:
            newarr    = []
            for i in arr[lvarstart+1:lvarend]:
                newarr.append(i.rstrip().lstrip())
            lvarnames  = []
            lvarstarts = []
            lvarends   = []
            for i in range(len(newarr)):
                line = newarr[i]
                lvarname = re.findall(r"(?<=<@)[a-zA-Z0-9\_\-]+",line)
                if len(lvarname) > 0 and not len(lvarname) > 1:
                    lvarnames.append(lvarname[0])
                elif len(lvarname) > 1:
                    raise MarkTwoParser(
                            specific_message="Multiple variables declared on same line. Invalid statement")
            for lvarname in lvarnames:
                start   = arrFind(f"<@{lvarname}>", newarr)
                end     = arrFind(f"<@/{lvarname}>", newarr)
                lvararr = newarr[start+1:end]
                self.lvars[lvarname] = lvararr

    def getLayout(self, arr:list, loc=None) -> None:
        def constructElement(line):
            elementstr    = line
            qelement      = MarkTwoElement()
            ename         = re.findall(r"[a-zA-Z0-9]+",elementstr)[0]
            qelement.qtag = ename
            elementstr    = elementstr.replace(ename,'',1).rstrip().lstrip()
            eattrs        = re.findall(r"[a-zA-Z0-9]+(?=\=[\'\"][a-zA-Z0-9\-\_\:\%\; ]+[\'\"])",elementstr)
            if len(eattrs) > 0:
                for attr in eattrs:
                    val = re.findall(f"(?<={attr}=[\'\"])[a-zA-Z0-9\-\_\:\%\; ]+(?=[\'\"])",elementstr)[0]
                    if attr == 'id':
                        qelement.qid = val
                    if attr == 'class':
                        classes = val.split(' ')
                        for clas in classes:
                            if clas.rstrip().lstrip() != '':
                                qelement.qclass.append(clas)
                                self.allClasses.append(clas)
                    if attr != 'class' and attr != 'id':
                        qelement.qattributes.append({attr:val})
                    substr     = f"{attr}=[\'\"]{val}[\"\']"
                    elementstr = re.sub(substr,'',elementstr).rstrip().lstrip()
            eprops        = re.findall(r"[a-zA-Z0-9]+(?!\=)",elementstr)
            eid           = re.findall(r"(?<=id=[\'\"])[a-zA-Z0-9]+(?=[\'\"])",elementstr)
            if len(eid) > 0:
                qelement.qid = eid[0]
                elementstr   = elementstr.replace(eid[0],'',1)
                elementstr   = re.sub(r"id=[\'\"][\'\"]",'',elementstr).lstrip().rstrip()
            qelement.generateHtml()
            return qelement

        locstr = None
        if loc == None: locstr = "main"
        else: locstr = loc
        layoutstart = arrFind('<!LAYOUT>',arr)
        layoutend   = arrFind('<!/LAYOUT>',arr)
        has = MarkTwoParser._blockStartEnd(layoutstart,layoutend,f"Layout Block ({locstr})")
        if has:
            newarr      = arr[layoutstart+1:layoutend]
            finalarr    = []
            nestpath    = []
            if loc == None:
                nestpath = [self.qdocument]
            elif loc == "header":
                nestpath = [self.hdocument]
            elif loc == "footer":
                nestpath = [self.fdocument]
            nestcount   = 0

            # replacevariables
            for i in range(len(newarr)):
                line = newarr[i].lstrip().rstrip()
                lvar = re.findall(r"(?<=<@)[a-zA-Z0-9\-\_]+",line)
                if len(lvar) > 0:
                    varname = lvar[0]
                    var = None
                    layoutvars = None
                    try:
                        layoutvars = self.lvars.copy()
                        var = layoutvars[varname].copy()
                    except:
                        raise MarkTwoParseError(
                                specific_message=f"Found undefined variable [{varname}] in layout.")
                    ids = re.findall(r"(?<=#)[a-zA-Z0-9]+(?=[\/#])",line)
                    idcount = 0
                    blankidp = r"(?<=\s)id(?=(\s|>))"
                    for eline in var:
                        idcount += len(re.findall(blankidp,eline))
                    if len(ids) == idcount:
                        idtopull = 0
                        for vline in var:
                            vlinehasid = regexHasOne(blankidp,vline)
                            if vlinehasid:
                                eid = ids[idtopull]
                                var[var.index(vline)] = re.sub(blankidp,f"id='{eid}'",vline,count=1)
                                idtopull += 1
                    else:
                        raise MarkTwoParseError(
                                specific_message=f"Defined variable [{varname}] not given correct # of ids.")
                    for j in var:
                        finalarr.append(j)
                else:
                    finalarr.append(line)
            # end replacevariables

            for i in range(len(finalarr)):
                inlineclose = False
                line = finalarr[i].lstrip().rstrip()

                #openp  = r"<[a-zA-Z0-9][a-zA-Z0-9\'\"\=\;\:\% ]+>"
                openp  = r"<(?!\/)[\S\s]+>"
                eopen  = re.findall(openp,line)
                openi  = [(m.start(0),m.end(0)) for m in re.finditer(openp,line)]
                hasopen = False
                if len(eopen) == 1:
                    eopen = eopen[0]
                    hasopen = True

                closep   = r"</[a-zA-Z0-9]+>"
                eclose   = re.findall(closep,line)
                closei   = [(m.start(0),m.end(0)) for m in re.finditer(closep,line)]
                closetag = None
                hasclose = False
                if len(eclose) == 1:
                    eclose = eclose[0]
                    hasclose = True
                    closetag = re.findall(r"(?<=<\/)[a-zA-Z0-9]+(?=>)",line)[0]

                estart = -1
                if len(openi) > 0:
                    estart = openi[0][0]

                eend = -1
                if len(closei) > 0:
                    eend = closei[0][0]

                if hasopen or hasclose:
                    autoclose   = line.count('/>') == 1
                    line        = line.replace('<','',1)
                    if not autoclose:
                        line = line.replace('>','',1)
                    else:
                        line = line.replace('/>','',1)
                        hasclose = True
                    ename       = re.findall(r"[a-zA-Z0-9]+",line)[0]
                    closepat    = f"</{ename}>"
                    inlineclose = line.count(closepat) == 1
                    if inlineclose:
                        line = line.replace(closepat,'')
                        hasclose = True

                    if hasopen:
                        qelement = constructElement(line)
                        if loc == None:
                            self.html += f"{qelement.opentag}"
                        elif loc == "header":
                            self.headhtml += f"{qelement.opentag}"
                        elif loc == "footer":
                            self.foothtml += f"{qelement.opentag}"

                        if loc == None:
                            if qelement.qid in self.content.keys():
                                self.html += f"{self.content[qelement.qid]}"
                        elif loc == "header":
                            if qelement.qid in self.headcontent.keys():
                                self.headhtml += f"{self.headcontent[qelement.qid]}"
                        elif loc == "footer":
                            if qelement.qid in self.footcontent.keys():
                                self.foothtml += f"{self.footcontent[qelement.qid]}"

                        nestpath[nestcount].qinner.append(qelement)
                        nestpath.append(nestpath[nestcount].qinner[len(nestpath[nestcount].qinner)-1])
                        nestcount += 1
                    if hasclose:
                        removedpath =  nestpath[nestcount:len(nestpath)]
                        removedpath =  removedpath[::-1]
                        for elem in removedpath:
                            if loc == None:
                                self.html += f"{elem.closetag}"
                            elif loc == "header":
                                self.headhtml += f"{elem.closetag}"
                            elif loc == "footer":
                                self.foothtml += f"{elem.closetag}"
                        nestpath    =  nestpath[0:nestcount]
                        nestcount   -= 1

    def getStyle(self, arr:list) -> None:
        self.css = ''
        self.css += self._getStyleClasses()
        if not self.options["nostyle"]:
            self._getDefaultStyle()
        stylestart = arrFind('<!CSS>',arr)
        styleend   = arrFind('<!/CSS>',arr)
        has = MarkTwoParser._blockStartEnd(stylestart,styleend,f"Style Block")
        if has:
            for i in range(stylestart+1,styleend):
                line = arr[i].rstrip()
                self.css += f"{line}"

    def getScript(self, arr:list) -> None:
        self.script = ""
        scriptstart = arrFind('<!JS>',arr)
        scriptend   = arrFind('<!/JS>',arr)
        has = MarkTwoParser._blockStartEnd(scriptstart,scriptend,f"Script Block")
        if has:
            self.script = ''
            for i in range(scriptstart+1,scriptend):
                line = arr[i].rstrip()
                self.script += f"{line}\n"

