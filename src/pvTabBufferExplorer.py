import vim
import os
import re

# for log
import logging
_logger = logging.getLogger('pve.TabBufferExplorer')

# basic buffer
from pyvim.pvBase import pvBuffer , PV_BUF_TYPE_ATTACH
from pyvim.pvBase import pvWindow
# tab buffer
from pyvim.pvTab import pvTabBuffer , pvTabBufferObserver
from pyvim.pvUtil import pvString
# for event
from pyvim.pvEvent import pvKeymapEvent , pvEventObserver , PV_KM_MODE_NORMAL
from pyvim.pvEvent import pvAutocmdEvent 
from pyvim.pvEvent import PV_EVENT_TYPE_KEYMAP , PV_EVENT_TYPE_AUTOCMD
# data model
from pyvim.pvDataModel import pvDataElement, PV_ELEMENT_TYPE_LEEF



class TabBufferExplorer( pvTabBufferObserver , pvEventObserver ):
    def __init__( self , target_win ):
        self.__target_win = target_win

        self.__buffer = pvTabBuffer()
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

    def analyzeBufferInfo( self ):
        _logger.debug('TabbedBufferExplorer::analyzeBufferInfo()')
        # get main window buffer
        buf_no = self.__target_win.bufferid
        update_selection = 0

        # init the buffer info
        self.__buffer.dataModel.removeAll()
        buffer_format = ' %(buffername)s[%(bufferid)2d] '

        for buffer in vim.buffers :
            # get properties
            ## buffer id
            buffer_id = buffer.number
            ## buffer_name
            buffer_basename = os.path.basename( buffer.name if buffer.name else "<NO NAME>" )
            ## internal status
            is_listed = vim.eval('getbufvar(%d,"&buflisted")' % buffer_id ) != '0'
            is_modifiable = vim.eval('getbufvar(%d,"&modifiable")' % buffer_id ) != '0'
            is_readonly = vim.eval('getbufvar(%d,"&readonly")' % buffer_id ) != '0'
            is_modified = vim.eval('getbufvar(%d,"&modified")' % buffer_id ) != '0'

            if is_listed :
                if buffer_id == buf_no :
                    update_selection = len ( self.__buffer.dataModel.root )
                name = pvString( MultibyteString = buffer_format % {
                        'bufferid' : buffer_id ,
                        'buffername' : buffer_basename } )
                self.__buffer.dataModel.addElement( pvDataElement.CreateElement( PV_ELEMENT_TYPE_LEEF , name ) )

        return update_selection
    
    def showBuffer( self , show_win ):
        _logger.debug('TabbedBufferExplorer::show()')
        self.__buffer.showBuffer( show_win )
        self.__buffer.updateBuffer( selection = self.analyzeBufferInfo() , notify = False )
        self.__target_win.setFocus()


    def OnSelectTabChanged( self , element ):
        _logger.debug('TabbedBufferExplorer::OnSelectTabChanged()')
        try :
            buffer_id = int( re.match('^ .*\[(?P<id>\s*\d+)] $' , element.name.MultibyteString ).group('id') )
        except:
            # not find valid buffer id, just do nothing
            return

        # buffer show at main window is just the buffer to show, do
        # nothing
        if buffer_id == self.__target_win.bufferid: 
            self.__target_win.setFocus()
            return

        # show the buffer on main panel
        show_buffer = pvBuffer( PV_BUF_TYPE_ATTACH )
        show_buffer.attach( buffer_id )
        show_buffer.showBuffer( self.__target_win )

        self.__target_win.setFocus()

        # sync the cwd
        if show_buffer.name != None :
            dir_path , file_name = os.path.split( show_buffer.name )
            if os.path.isdir( dir_path ): os.chdir( dir_path )


    def OnProcessEvent( self , event ):
        if event.type == PV_EVENT_TYPE_KEYMAP and event.key_name == '<f5>' :
            self.__buffer.updateBuffer( selection = self.analyzeBufferInfo() , notify = False ) 

        elif event.type == PV_EVENT_TYPE_KEYMAP and event.key_name == 'dd':
            # one buffer , can't delete it
            if len ( self.__buffer.dataModel.root ) == 1: return
            # check if select a valid item
            current_item_index = self.__buffer.searchIndexByCursor()
            if current_item_index == -1 : return
            current_item = self.__buffer.dataModel.root.childNodes[ current_item_index ]

            # if delete the current selected one , just move down on item
            if current_item_index == self.__buffer.selection :
                self.__buffer.updateBuffer( selection = self.__buffer.selection + 1 )


            # if delete , move the selection
            if self.__buffer.selection > current_item_index :
                after_selection = self.__buffer.selection - 1
            else:
                after_selection = self.__buffer.selection

            # analyze the buffer id
            try :
                buffer_id = int ( re.match('^{(?P<id>\s*\d+)}.*$' , current_item.name.MultibyteString ).group('id') )
            except:
                return

            # delete buffer
            delete_buffer = pvBuffer( PV_BUF_TYPE_ATTACH )
            delete_buffer.attach( buffer_id )
            delete_buffer.wipeout()
            # delete list item
            self.__buffer.dataModel.removeByElement( current_item )

            self.__buffer.updateBuffer( selection = after_selection , notify = False )

        elif event.type == PV_EVENT_TYPE_AUTOCMD and  ( ( event.autocmd_name == 'bufenter' and self.__target_win == pvWindow() ) or ( event.autocmd_name == 'bufdelete' ) ): 
            self.__buffer.updateBuffer( selection = self.analyzeBufferInfo() , notify = False )
        else:
            super( pvTabBufferExplorer , self ).OnProcessEvent( event )

class Application( pvEventObserver ):
    def __init__( self ):
        self.buffer = None
        self.window = None
        self.event = pvKeymapEvent( '<m-1>' , PV_KM_MODE_NORMAL  )
        
    def OnProcessEvent( self , event ):
        if self.buffer is None and self.window is None :
            current_window = pvWindow()
            from pyvim.pvBase import pvWinSplitter , PV_SPLIT_TYPE_CUR_BOTTOM
            self.window = pvWinSplitter( PV_SPLIT_TYPE_CUR_BOTTOM , ( -1 , 1 ) , current_window ).doSplit()
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



