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
from pyvim.pvDataModel import pvDataElement, PV_ELEMENT_TYPE_LEEF , PV_ELEMENT_TYPE_ROOT



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

    def updateDataModel( self ):
        _logger.debug('TabbedBufferExplorer::analyzeBufferInfo()')
        # get main window buffer
        current_show_buffer_no = self.__target_win.bufferid

        # init the buffer info
        self.__buffer.dataModel.removeAll()
        buffer_format = ' %(buffername)s[%(bufferid)2d] '

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

            name = pvString( MultibyteString = buffer_format % {
                    'bufferid' : buffer_id ,
                    'buffername' : buffer_basename } )
            new_element = pvDataElement.CreateElement( PV_ELEMENT_TYPE_LEEF , name ) 
            self.__buffer.dataModel.addElement( new_element )
            if buffer_id == current_show_buffer_no:
                self.__buffer.dataModel.selectedElement = new_element



    def showBuffer( self , show_win ):
        _logger.debug('TabbedBufferExplorer::show()')
        self.__buffer.showBuffer( show_win )
        self.__buffer.updateBuffer()
        self.__target_win.setFocus()


    def OnTabSelect( self , element ):
        # first open
        if element.type == PV_ELEMENT_TYPE_ROOT:
            self.updateDataModel()
            return

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
            self.updateDataModel()
            self.__buffer.updateBuffer()

        elif event.type == PV_EVENT_TYPE_KEYMAP and event.key_name == 'dd':
            # one buffer , can't delete it, ignore the event
            if self.__buffer.dataModel.root.count() == 1: return
            # check if select a valid item
            current_element = self.__buffer.getElementUnderCursor()
            if current_element == None : return

            # if delete the current selected one , just move down on item
            if current_element == self.__buffer.dataModel.selectedElement:
                next_element = current_element.nextSibling
                if next_element == None :
                    next_element = self.__buffer.dataModel.root.childNodes[0]
                self.__buffer.dataModel.selectedElement = next_element

                try :
                    move_buffer_id = int( 
                            re.match(
                                '^ .*\[(?P<id>\s*\d+)] $' , 
                                next_element.name.MultibyteString ).group('id') )
                except:
                    # not find valid buffer id, just do nothing
                    return

                # display the next buffer
                move_buffer = pvBuffer( PV_BUF_TYPE_ATTACH )
                move_buffer.attach( move_buffer_id )
                move_buffer.showBuffer( self.__target_win )
                self.__buffer.updateBuffer()

            # analyze the buffer id
            try :
                delete_buffer_id = int ( 
                        re.match(
                            '^ .*\[(?P<id>\s*\d+)] $' , 
                            current_element.name.MultibyteString ).group('id') )
            except:
                return

            # delete buffer
            delete_buffer = pvBuffer( PV_BUF_TYPE_ATTACH )
            delete_buffer.attach( delete_buffer_id )
            delete_buffer.wipeout()
            # delete list item
            self.updateDataModel()
            self.__buffer.updateBuffer()


        elif event.type == PV_EVENT_TYPE_AUTOCMD and  \
                ( ( event.autocmd_name == 'bufenter' and self.__target_win == pvWindow() ) or \
                ( event.autocmd_name == 'bufdelete' ) ): 
                    self.updateDataModel()
                    self.__buffer.updateBuffer()

class Application( pvEventObserver ):
    def __init__( self ):
        self.buffer = None
        self.window = None
        self.event = pvKeymapEvent( '<m-1>' , PV_KM_MODE_NORMAL  )
        
    def OnProcessEvent( self , event ):
        try :
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
        except:
            import sys
            print sys.exc_info()
            print sys.exc_info()[2].tb_frame.f_code

    def start( self ):
        self.event.registerObserver( self )

    def stop( self ):
        self.event.removeObserver( self )



