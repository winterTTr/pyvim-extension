from pyvim.pvEvent import pvKeymapEvent , PV_KM_MODE_NORMAL , pvEventObserver
from pyvim.pvBase import pvWindow , pvWinSplitter 
from pyvim.pvBase import PV_SPLIT_TYPE_MOST_LEFT , PV_SPLIT_TYPE_MOST_RIGHT , PV_SPLIT_TYPE_CUR_BOTTOM 

from pvBufferExplorer import pvBufferExplorer
from pvFileExplorer import pvFileExplorer



PV_EP_LEFT = 0x01
PV_EP_RIGHT = 0x02

class Application( pvEventObserver ):
    def __init__( self , shortcut_key , which_side = PV_EP_LEFT ):
        self.side = which_side

        self.bexp_window = None
        self.bexp_buffer = None
        self.fexp_window = None
        self.fexp_buffer = None

        self.event = pvKeymapEvent( shortcut_key , PV_KM_MODE_NORMAL  )


    def OnProcessEvent( self , event ):
        isNotStart = self.bexp_window == None \
                or self.fexp_window == None \
                or ( not self.bexp_window.isShown() ) \
                or ( not self.fexp_window.isShown() )

        self.cleanup()
        if isNotStart :
            self.constructAndShow()


    def cleanup( self ):
        if self.bexp_window :
            self.bexp_window.closeWindow()
        self.bexp_window = None

        if self.fexp_window :
            self.fexp_window.closeWindow()
        self.fexp_window = None

        if self.bexp_buffer:
            self.bexp_buffer.destroy()
        self.bexp_buffer = None

        if self.fexp_buffer:
            self.fexp_buffer.destroy()
        self.fexp_buffer = None



    def constructAndShow( self ):
        current_window = pvWindow()
        self.bexp_window = pvWinSplitter( 
                PV_SPLIT_TYPE_MOST_LEFT if self.side == PV_EP_LEFT else PV_SPLIT_TYPE_MOST_RIGHT, 
                ( 35 , -1 ) , 
                current_window ).doSplit()

        self.fexp_window = pvWinSplitter(
                PV_SPLIT_TYPE_CUR_BOTTOM , 
                ( -1 , 30 ) , 
                self.bexp_window ).doSplit()

        from pyvim.pvLinear import PV_LINEARBUF_TYPE_VERTICAL
        self.bexp_buffer = pvBufferExplorer( PV_LINEARBUF_TYPE_VERTICAL , current_window )
        self.bexp_buffer.showBuffer( self.bexp_window )

        self.fexp_buffer = pvFileExplorer( current_window )
        self.fexp_buffer.showBuffer( self.fexp_window )


    def start( self ):
        self.event.registerObserver( self )
        
    def stop( self ):
        self.event.removeObserver( self )



