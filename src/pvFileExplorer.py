import os
import sys
import types
import os.path


from pyvim.pvBase import pvBuffer , PV_BUF_TYPE_NORMAL , PV_BUF_TYPE_ATTACH
from pyvim.pvBase import pvWindow
from pyvim.pvUtil import pvString

from pyvim.pvEvent import pvEventObserver , pvKeymapEvent , PV_KM_MODE_NORMAL

from pyvim.pvTree import pvTreeBuffer , pvTreeBufferObserver
from pyvim.pvDataModel import pvModelIndex , pvAbstractModel , PV_MODEL_ROLE_DISPLAY


class pvFileSystemNode(object):
    def __init__( self ):
        self.index = None

        self.path = u""
        self.children = []

    def __eq__( self , node ):
        if type( node )!= pvFileSystemNode:
            return False
        return self.path == node.path

class pvFileSystemModel( pvAbstractModel , pvTreeBufferObserver ):
    def __init__(self):
        self.root = pvFileSystemNode()
        self.root.index = pvModelIndex()

    def rowCount( self ,  index ):
        if sys.platform[:3] == 'win' and ( not index.isValid() ):
            if len( self.root.children ):
                return len( self.root.children )

            import string
            for x in string.ascii_uppercase :
                driver_path = u'%s:\\' % x
                if os.path.isdir( driver_path ):
                    newIndex = self.createIndex( len( self.root.children ) , None )
                    # create new node
                    newNode = pvFileSystemNode()
                    newNode.index = newIndex
                    newNode.path = driver_path
                    newIndex.data = newNode
                    self.root.children.append( newNode )
            return len( self.root.children )
        else:
            parent_node = index.data if index.isValid() else self.root
            if len( parent_node.children ): return len( parent_node.children )
            for each_name in os.listdir( parent_node.path ):
                newIndex = self.createIndex( len( parent_node.children ) , None )
                # create new node
                newNode = pvFileSystemNode()
                newNode.index = newIndex
                newNode.path = os.path.join( parent_node.path , each_name )
                newIndex.data = newNode
                parent_node.children.append( newNode )

            return len( parent_node.children )
                    

    def index( self , row , pindex ):
        pnode = pindex.data if pindex.isValid() else self.root
        return pnode.children[row].index

    def indexByPath( self , full_path ):
        if full_path == "" or full_path is None: return pvModelIndex()

        if type( full_path ) != types.UnicodeType:
            full_path = pvString.fromVim( full_path ).unicode

        path_list = []
        phead , pend = os.path.split( full_path )
        while pend :
            path_list.insert( 0 , pend )
            phead , pend = os.path.split( phead )
        path_list.insert( 0 , phead )
        if sys.platform[:3] == 'win':
            path_list = map( lambda x : x.replace( '/' , '\\' ) , path_list )

        plus_path = u""
        node = self.root
        while path_list :
            plus_path = os.path.join( plus_path , path_list.pop(0) )
            if self.rowCount( node.index ) == 0 :
                return pvModelIndex()

            try:
                node = filter( lambda x : x.path == plus_path , node.children )[0]
            except:
                return pvModelIndex()

        return node.index




    def data( self , index , role = PV_MODEL_ROLE_DISPLAY ):
        basename = os.path.basename( index.data.path )
        return pvString.fromUnicode( basename if basename else index.data.path )


    def parent( self , index ):
        if not index.isValid(): return pvModelIndex()
        path = index.data.path
        ppath = os.path.split( path )[0]
        return self.root.index if path == ppath else self.indexByPath( ppath )

    def hasChildren( self , index ):
        return os.path.isdir( index.data.path ) 

    def OnTreeNodeSelected( self  , index ):
        pass

    def OnTreeNodeExpanded( self  , index ):
        pass

    def OnTreeNodeCollapsed( self  , index ):
        index.data.children = []


class pvFileExplorer( pvTreeBufferObserver ):
    def __init__( self  , target_window ):
        self.__buffer = pvTreeBuffer( pvFileSystemModel() )
        self.__buffer.registerObserver( self )
        self.__buffer.registerObserver( self.__buffer.model )

        self.__target_window = target_window

        bufferid = target_window.bufferid
        tmpBuf = pvBuffer( PV_BUF_TYPE_ATTACH )
        tmpBuf.attach( bufferid )
        index = self.__buffer.model.indexByPath( tmpBuf.name )
        self.__buffer.expandTo( index )
        tmpBuf.detach()


    def destroy( self ):
        self.__buffer.wipeout()
        self.__buffer = None


    def OnTreeNodeSelected( self , index ):
        path = index.data.path
        if os.path.isdir( path ):
            os.chdir( path )
        else:
            buffer = pvBuffer( PV_BUF_TYPE_NORMAL , path )
            buffer.showBuffer( self.__target_window )
            buffer.detach()
            self.__target_window.setFocus()

    def OnTreeNodeExpanded( self ,index ):
        pass

    def OnTreeNodeCollapsed( self , index ):
        pass

    def showBuffer( self , show_win ):
        self.__buffer.showBuffer( show_win )
        self.__buffer.updateBuffer()
        self.__target_window.setFocus()

class Application( pvEventObserver ):
    def __init__( self , hotkey ):
        self.buffer = None
        self.window = None
        self.event = pvKeymapEvent( hotkey , PV_KM_MODE_NORMAL  )
        
    def OnProcessEvent( self , event ):
        if self.buffer is None and self.window is None :
            current_window = pvWindow()
            from pyvim.pvBase import pvWinSplitter , PV_SPLIT_TYPE_MOST_LEFT
            self.window = pvWinSplitter( PV_SPLIT_TYPE_MOST_LEFT , ( 30 , -1 ) , current_window ).doSplit()
            self.buffer = pvFileExplorer( current_window )
            self.buffer.showBuffer( self.window )
        else:
            if self.window:
                self.window.closeWindow()
                self.window = None
            if self.buffer:
                self.buffer.destroy()
                self.buffer = None

    def start( self ):
        self.event.registerObserver( self )

    def stop( self ):
        self.event.removeObserver( self )



        

