from models.marktwoparser import MarkTwoParser

class FooterHtmlTest:
    testtype  = "FOOTER HTML"
    name      = None
    accepted  = None
    testinput = None
    response  = None
    passed    = None

    def __init__(self,name,layoutin=None,contentin=None,varin=None,accepted=None):
        self.name = name
        self.testinput = ""
        if contentin != None:
            self.testinput  = f"_FOOTCONTENT|\n{contentin}\n|FOOTCONTENT_\n\n"
        if layoutin != None:
            self.testinput += f"_FOOTLAYOUT|\n{layoutin}\n|FOOTLAYOUT_\n\n"
        if varin != None:
            self.testinput += f"@LAYOUT|\n{varin}\n|LAYOUT@"
        self.accepted = accepted

    def __repr__(self):
        return f"<FooterHtmlTest: {self.name} = {self.passed}>"

    def run(self,options):
        self.response = MarkTwoParser(options=options,
                                    testinput=self.testinput).foothtml
        self.passed   = self.response == self.accepted

    @staticmethod
    def get():
        tests = []
        tests.append(FooterHtmlTest("Single Element",
                              layoutin="_p#Id||_",
                              contentin="#Id Paragraph Tag",
                              accepted="<p id=\"Id\">Paragraph Tag</p>"))

        tests.append(FooterHtmlTest("Multi Element",
                              layoutin=("_div|\n"
                                            "_p#Id||_\n"
                                        "|div_"),
                              contentin="#Id lorem ipsum",
                              accepted="<div><p id=\"Id\">lorem ipsum</p></div>"))

        tests.append(FooterHtmlTest("Complex Nesting / Elements",
                              layoutin=("_div#Id.class[width=20,height=30,hidden]|\n"
                                            "_p#P1[onclick=someMethod]||_\n"
                                            "_table|\n"
                                                "_tbody|\n"
                                                    "_tr|\n"
                                                        "_td#TD1||_\n"
                                                        "_td#TD2||_\n"
                                                        "_td#TD3||_\n"
                                                    "|tr_\n"
                                                "|tbody_\n"
                                            "|table_\n"
                                        "|div_"),
                              contentin=("#P1  This is a paragraph\n"
                               "#TD1 Cell 1\n"
                               "#TD2 Cell 2\n"
                               "#TD3 This is the third cell,\n"
                               "     I am just testing a multi line.\n"),
                              accepted=("<div id=\"Id\" class=\"class\" width=\"20\" height=\"30\" hidden>"
                                            "<p id=\"P1\" onclick=\"someMethod\">"
                                                "This is a paragraph"
                                            "</p>"
                                            "<table>"
                                                "<tbody>"
                                                    "<tr>"
                                                        "<td id=\"TD1\">"
                                                            "Cell 1"
                                                        "</td>"
                                                        "<td id=\"TD2\">"
                                                            "Cell 2"
                                                        "</td>"
                                                        "<td id=\"TD3\">"
                                                            "This is the third cell, "
                                                            "I am just testing a multi line."
                                                        "</td>"
                                                    "</tr>"
                                                "</tbody>"
                                            "</table>"
                                        "</div>")))

        tests.append(FooterHtmlTest("Variable Assignment",
                              varin=("@var|\n"
                                         "_p#||_\n"
                                         "_p#||_\n"
                                         "_p#||_\n"
                                     "|var@"),
                              layoutin="@var#Id1#Id2#Id3@",
                              contentin=("#Id1 This\n"
                                         "#Id2 is a\n"
                                         "#Id3 variable."),
                              accepted=("<p id=\"Id1\">"
                                            "This"
                                        "</p>"
                                        "<p id=\"Id2\">"
                                            "is a"
                                        "</p>"
                                        "<p id=\"Id3\">"
                                            "variable."
                                        "</p>")))

        tests.append(FooterHtmlTest("Variable With A Preset Id",
                              varin=("@var|\n"
                                         "_div#Vdiv|\n"
                                             "_p#||_\n"
                                             "_p#||_\n"
                                         "|div_\n"
                                     "|var@"),
                              layoutin="@var#P1#P2@",
                              contentin=("#P1 Paragraph 1\n"
                                         "#P2 Paragraph 2"),
                              accepted=("<div id=\"Vdiv\">"
                                            "<p id=\"P1\">"
                                                "Paragraph 1"
                                            "</p>"
                                            "<p id=\"P2\">"
                                                "Paragraph 2"
                                            "</p>"
                                        "</div>")))
        return tests
