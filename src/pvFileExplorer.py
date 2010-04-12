import os


from pyvim.pvBase import pvBuffer , PV_BUF_TYPE_ATTACH
from pyvim.pvBase import pvWindow
from pyvim.pvUtil import pvString

from pyvim.pvEvent import pvEventObserver , pvKeymapEvent , PV_KM_MODE_NORMAL

from pyvim.pvTree import pvTreeBuffer , pvTreeBufferObserver
from pyvim.pvDataModel import PV_ELEMENT_TYPE_LEEF , PV_ELEMENT_TYPE_BRANCH ,  PV_ELEMENT_TYPE_ROOT
from pyvim.pvDataModel import pvDataElement 
from pyvim.pvDataModel import PV_BRANCH_STATUS_CLOSE , PV_BRANCH_STATUS_OPEN


class pvFileExplorer( pvTreeBufferObserver ):
    def __init__( self  , target_window ):
        self.__buffer = pvTreeBuffer()
        self.__buffer.registerObserver( self )
        self.__target_window = target_window


    def destroy( self ):
        self.__buffer.wipeout()
        self.__buffer = None


    def OnElementSelect( self , element ):
        if element.type == PV_ELEMENT_TYPE_ROOT:
            buf_no = self.__target_window.bufferid
            if buf_no == -1 :
                cwd = os.getcwdu() # unicode current work directory
            else:
                buf = pvBuffer( PV_BUF_TYPE_ATTACH )
                buf.attach( buf_no )
                cwd = pvString( MultibyteString = buf.name ).UnicodeString
                if cwd == u"" :
                    cwd = os.getcwdu() # unicode current work directory

            if cwd == u"":
                return

            # find the exist part
            while not os.path.exists( cwd ):
                cwd , tail = os.path.split( cwd )
                if tail == u'': 
                    if cwd[-1] == '/': cwd = cwd[:-1] + '\\'
                    break

            # split into each part
            cwd_list = []
            while True:
                cwd , tail = os.path.split( cwd )
                if tail == u'': 
                    if cwd[-1] == '/': cwd = cwd[:-1] + '\\'
                    cwd_list.insert( 0 , pvString( UnicodeString = cwd ) )
                    break

                cwd_list.insert( 0 ,  pvString( UnicodeString = tail ) )


            # update data model into the current status

            # 1 . update base disk flag
            import string
            for x in string.ascii_uppercase :
                driver_path = u'%s:\\' % x
                if os.path.isdir( driver_path ):
                    # create element
                    element = pvDataElement.CreateElement(
                                PV_ELEMENT_TYPE_BRANCH , 
                                pvString( UnicodeString = driver_path ) , 
                                PV_BRANCH_STATUS_CLOSE ) 
                    # and add to data model
                    self.__buffer.dataModel.addElement( self.__buffer.dataModel.root , element )
                    if element.name == cwd_list[0]: 
                        self.__buffer.dataModel.selectedElement = element
                        cwd_list.pop(0)


            ## 2. expand other
            change_flag = False
            base_path = u"" 
            while cwd_list :
                former_selected_element = self.__buffer.dataModel.selectedElement
                former_selected_element.status = PV_BRANCH_STATUS_OPEN
                base_path = os.path.join( base_path , former_selected_element.name.UnicodeString )
                change_flag = False
                for each_name in os.listdir( base_path ):
                    element = pvDataElement.CreateElement(
                            PV_ELEMENT_TYPE_BRANCH \
                                    if os.path.isdir( os.path.join( base_path , each_name ) ) \
                                    else PV_ELEMENT_TYPE_LEEF, 
                            pvString( UnicodeString = each_name ) , 
                            PV_BRANCH_STATUS_CLOSE ) 
                    self.__buffer.dataModel.addElement( former_selected_element , element )
                    if not change_flag and element.name == cwd_list[0] :
                        self.__buffer.dataModel.selectedElement = element
                        cwd_list.pop(0)
                        change_flag = True




    def showBuffer( self , show_win ):
        self.__buffer.showBuffer( show_win )
        self.__buffer.updateBuffer()
        self.__target_window.setFocus()




class Application( pvEventObserver ):
    def __init__( self ):
        self.buffer = None
        self.window = None
        self.event = pvKeymapEvent( '<m-2>' , PV_KM_MODE_NORMAL  )
        
    def OnProcessEvent( self , event ):
        try:
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
        except:
            import sys
            print sys.exc_info()
            print sys.exc_info()[2].tb_frame.f_code

    def start( self ):
        self.event.registerObserver( self )

    def stop( self ):
        self.event.removeObserver( self )



        

