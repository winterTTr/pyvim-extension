import vim
import re
import sys
import os

def DoxygenMenuInit():
    vim.command('silent! nnoremenu <silent> p&yvimex.&doxygen.CPlusPlus.file          :py pvDoxygen.CPP.DgFile()<CR>')
    vim.command('silent! nnoremenu <silent> p&yvimex.&doxygen.CPlusPlus.function      :py pvDoxygen.CPP.DgFunction()<CR>')
    vim.command('silent! nnoremenu <silent> p&yvimex.&doxygen.CPlusPlus.class&&struct :py pvDoxygen.CPP.DgClass()<CR>')


def DgGetIndent():
    ret = re.match('^(?P<indent>\s*).*$' , vim.current.line )
    if ret :
        return ret.group('indent')
    else:
        return ""


class CPP(object):
    @staticmethod
    def DgFile():
        full_path = vim.current.buffer.name
        filename = os.path.split( full_path )[1] if full_path else ""

        insertContent = [
                "/*!",
                " * \\file     %s" % ( filename , ) ,
                " * \\brief    :add brief:" ,
                " * \\author   winterTTr" ,
                " * \\version  $Revision$" , 
                " * \\date     $Date$",
                " * \\bug      :add bug:",
                " *",
                " * :add detail:",
                " */",
                "",
                ""]
        vim.current.buffer[0:0] = insertContent

    @staticmethod
    def DgFunction():
        reFunction = re.compile( """
            ^
            (?P<indent>\s*)
            (?P<status>(static|virtual)\s+)?
            (?P<return>(const\s+)?\w+(\s*[*&])*\s+)?
            (?P<name>[~\w]+)
            \s*
            \(
            (?P<sig>.*)
            \)
            \s*
            (const)?
            \s*
            (=\s*0)?
            \s*
            ;?
            \s*
            $
            """ , re.VERBOSE )
        ret = reFunction.match( vim.current.line )
        if not ret :
            sys.stderr.write( 'The current line does not seem a valid function decleration!')
            return

        # strip the spaces in items
        reFunctionDict = ret.groupdict()
        for key in reFunctionDict.keys():
            if reFunctionDict[key] != None :
                if key != 'indent' :
                    reFunctionDict[key] = reFunctionDict[key].strip()
            else:
                reFunctionDict[key] = ""

        # anylize the signature
        #(?P<type>(const\s+)?\w+(\s*[*&])*)
        reParam = re.compile( """
            ^
            \s*
            (?P<type>.*)
            \s+
            (?P<name>\w+)
            \s*
            (\[[\s\d]*\])?
            \s*
            $
            """ , re.VERBOSE )

        sigNameList = []
        if len( reFunctionDict['sig'] ) != 0 :
            for x in reFunctionDict['sig'].split(','):
                ret =  reParam.match( x )
                if ret :
                    sigNameList.append( ret.group('name') )

        insertContent =     [ "/*!" ]
        insertContent.append( " * \\brief    :add brief:" )

        for name in sigNameList :
            insertContent.append( " * \\param[in,out]  %s   :add param:" % name )

        if reFunctionDict['return'] != "" and reFunctionDict['return'] != 'void':
            insertContent.append( " * \\return    :add return:" )

        insertContent.append( " * \\sa       :add seealso:" )
        insertContent.append( " *")
        insertContent.append( " * :add detail:" )
        insertContent.append( " */")

        insertContent = map( lambda x : reFunctionDict['indent'] + x , insertContent )


        curLine = vim.current.window.cursor[0] - 1
        vim.current.buffer[curLine:curLine] = insertContent

    @staticmethod
    def DgClass():
        reClass = re.compile( """
            ^
            (?P<indent>\s*)
            (?P<type>class|struct)
            \s+
            (?P<name>\w+)
            \s*
            (?P<inherit>:[^{]*)?
            ({.*)?
            (}.*)?
            ;?
            $
            """ , re.VERBOSE )
        ret = reClass.match( vim.current.line )
        if not ret :
            sys.stderr.write( 'The current line does not seem a valid class decleration!')
            return

        reClassDict = ret.groupdict()

        reInherit = re.compile( """
            ^
            (?P<level>public|private|protected)
            \s+
            (?P<name>\w+)
            $
            """ , re.VERBOSE )

        offset = reClassDict['inherit'].find(":")
        if offset != -1:
            reClassDict['inherit'] = reClassDict['inherit'][offset+1:]

        inheritClassList = reClassDict['inherit'].split(',') if reClassDict['inherit'] else []
        inheritClassList = map( lambda x : x.strip() , inheritClassList )
        inheritClassNameList = []
        for c in inheritClassList:
            ret = reInherit.match( c )
            if ret :
                inheritClassNameList.append( ret.group('name') )

        full_path = vim.current.buffer.name
        filename = os.path.split( full_path )[1] if full_path else ""

        insertContent =     [ "/*!" ]
        insertContent.append( " * \\%(type)-6s   %(classname)s  %(filename)s" % { 
                'type'      : reClassDict['type'] ,
                'classname' : reClassDict['name'] , 
                'filename'  : filename } )
        insertContent.append( " * \\brief    :add brief:")
        insertContent.append( " * \\sa       %s" % ( ','.join( inheritClassNameList) if inheritClassNameList else ":add seealso:" ,  ) )
        insertContent.append( " *")
        insertContent.append( " * :add detail:")
        insertContent.append( " */")

        curLine = vim.current.window.cursor[0] - 1
        vim.current.buffer[curLine:curLine] = insertContent










