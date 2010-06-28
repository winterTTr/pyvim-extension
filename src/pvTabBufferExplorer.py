import vim
import os
import re

# for log
import logging
_logger = logging.getLogger('pve.pvTabBufferExplorer')

# basic buffer
from pyvim.pvBase import pvBuffer , PV_BUF_TYPE_ATTACH
from pyvim.pvBase import pvWindow
# tab buffer
from pyvim.pvLinear import pvLinearBuffer , pvLinearBufferObserver 
from pyvim.pvLinear import PV_LINEARBUF_TYPE_HORIZONTAL , PV_LINEARBUF_TYPE_VERTICAL
from pyvim.pvUtil import pvString
# for event
from pyvim.pvEvent import pvEventObserver 
from pyvim.pvEvent import pvAutocmdEvent , pvKeymapEvent , PV_KM_MODE_NORMAL
from pyvim.pvEvent import PV_EVENT_TYPE_KEYMAP , PV_EVENT_TYPE_AUTOCMD
# data model
from pyvim.pvDataModel import pvAbstractModel , PV_MODEL_ROLE_DISPLAY , pvModelIndex



class pvBufferInfoModelNode(object):
    def __init__( self ):
        self.index = None
        self.name = ""


class pvBufferInfoModel( pvAbstractModel ):
    def __init__( self ):
        self.__cache = []

    def rowCount( self , index ):
        if index.isValid() : return 0

        # init the buffer info
        self.__cache = []

        for buffer in vim.buffers :
            ## buffer id
            buffer_id = buffer.number
            ## buffer_name
            buffer_basename = os.path.basename( buffer.name ) if buffer.name else "<NO NAME>" 
            ## internal status
            is_listed = vim.eval('getbufvar(%d,"&buflisted")' % buffer_id ) != '0'
            #is_modifiable = vim.eval('getbufvar(%d,"&modifiable")' % buffer_id ) != '0'
            #is_readonly = vim.eval('getbufvar(%d,"&readonly")' % buffer_id ) != '0'
            #is_modified = vim.eval('getbufvar(%d,"&modified")' % buffer_id ) != '0'
            if not is_listed:
                continue

            item = pvBufferInfoModelNode()
            item.index = self.createIndex( len( self.__cache ) , buffer_id )
            item.name = buffer_basename

            self.__cache.append( item )


        return len( self.__cache )


    def index( self , row , pindex ):
        if pindex.isValid() or  row >= len( self.__cache ) : return pvModelIndex()
        return self.__cache[ row ].index

    def data( self , index , role = PV_MODEL_ROLE_DISPLAY ):
        if not index.isValid():
            return pvString()

        item = filter( lambda x : x.index == index , self.__cache )[0]
        return pvString.fromVim( item.name )

    def indexById( self , buffer_id ):
        self.rowCount( pvModelIndex() )
        item = filter( lambda x : x.index.data == buffer_id , self.__cache )
        if len( item ):
            return item[0].index
        else:
            return pvModelIndex()






class TabBufferExplorer( pvLinearBufferObserver , pvEventObserver ):
    def __init__( self , target_win ):
        self.__target_win = target_win
        self.__buffer = pvLinearBuffer( pvBufferInfoModel() , PV_LINEARBUF_TYPE_VERTICAL )
        self.__buffer.registerObserver( self )

        self.__event = []
        self.__event.append( pvKeymapEvent( "<F5>" , PV_KM_MODE_NORMAL , self.__buffer ) )
        self.__event.append( pvKeymapEvent( "dd"   , PV_KM_MODE_NORMAL , self.__buffer ) )
        self.__event.append( pvAutocmdEvent( 'pvTabBufferExplorer' ,  'BufEnter' , '*' ) )
        self.__event.append( pvAutocmdEvent( 'pvTabBufferExplorer' ,  'BufDelete' , '*') )

        #register event
        for event in self.__event: event.registerObserver( self )

    def destroy( self ):
        #unregister event
        for event in self.__event : event.removeObserver( self )
        # remove observer
        self.__buffer.removeObserver( self )
        # destroy buffer
        self.__buffer.wipeout()

    def showBuffer( self , show_win ):
        _logger.debug('TabbedBufferExplorer::show()')
        self.__buffer.showBuffer( show_win )
        self.__buffer.selection = self.__buffer.model.indexById( self.__target_win.bufferid )
        self.__buffer.updateBuffer()
        self.__target_win.setFocus()


    def OnLinearItemSelected( self , index ):
        # show the buffer on main panel
        show_buffer = pvBuffer( PV_BUF_TYPE_ATTACH )
        show_buffer.attach( index.data )
        show_buffer.showBuffer( self.__target_win )
        self.__target_win.setFocus()
        # sync the cwd
        if show_buffer.name != None :
            dir_path , file_name = os.path.split( show_buffer.name )
            if os.path.isdir( dir_path ): os.chdir( dir_path )


    def OnProcessEvent( self , event ):
        if event.type == PV_EVENT_TYPE_KEYMAP and event.key_name == '<f5>' :
            self.__buffer.updateBuffer()

        elif event.type == PV_EVENT_TYPE_KEYMAP and event.key_name == 'dd':
            import sockpdb
            sockpdb.set_trace()
            # one buffer , can't delete it, ignore the event
            if self.__buffer.model.rowCount( pvModelIndex() ) == 1 : return

            index = self.__buffer.indexAtCursor( vim.current.window.cursor )
            if not index.isValid() : return 

            if index == self.__buffer.selection:
                nindex = self.__buffer.model.index( index.row + 1 , pvModelIndex() )
                if not nindex.isValid():
                    nindex = self.__buffer.model.index( 0 , pvModelIndex() )
                self.__buffer.selection = nindex
                # show the buffer on main panel
                show_buffer = pvBuffer( PV_BUF_TYPE_ATTACH )
                show_buffer.attach( nindex.data )
                show_buffer.showBuffer( self.__target_win )

            # delete buffer
            delete_buffer = pvBuffer( PV_BUF_TYPE_ATTACH )
            delete_buffer.attach( index.data )
            delete_buffer.wipeout()
            # delete list item
            self.__buffer.updateBuffer()

        elif event.type == PV_EVENT_TYPE_AUTOCMD and  \
                ( ( event.autocmd_name == 'bufenter' and self.__target_win == pvWindow() ) or \
                ( event.autocmd_name == 'bufdelete' ) ):
            import sockpdb
            sockpdb.set_trace()
            self.__buffer.selection = self.__buffer.model.indexById( self.__target_win.bufferid )
            self.__buffer.updateBuffer()

class Application( pvEventObserver ):
    def __init__( self ):
        self.buffer = None
        self.window = None
        self.event = pvKeymapEvent( '<m-1>' , PV_KM_MODE_NORMAL  )
        
    def OnProcessEvent( self , event ):
        if self.buffer is None and self.window is None :
            current_window = pvWindow()
            from pyvim.pvBase import pvWinSplitter , PV_SPLIT_TYPE_CUR_BOTTOM , PV_SPLIT_TYPE_CUR_LEFT
            self.window = pvWinSplitter( PV_SPLIT_TYPE_CUR_LEFT , ( 30 , -1 ) , current_window ).doSplit()
            self.buffer = TabBufferExplorer( current_window )
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



