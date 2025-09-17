import sys
import pyqtgraph as pg
import matplotlib.pyplot as plt #might not be used
from PyQt6.QtWidgets import QApplication,QWidget,QLineEdit, QMainWindow, QLabel, QVBoxLayout, QPushButton

from pytubefix import YouTube,extract

#Starting window
class MainWindow(QMainWindow): 
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Comment Analyzer")
        self.resize(1200, 600) # Set initial size
        self.center_on_screen() #Center the window, only needed for testing 
        #text 
        self.linkPrompt = QLabel(self)
       
        #All these have "self" next to them so they can be called outside of here.
        self.commentsAnalyzed= QLabel(self) #Return number of comments analyzed (Need some way to count them)
        self.sentimentReturn = QLabel(self) #Return sentiment summary
        self.linkReturn = QLabel(self) #Read link back to user
        self.linkReturn.setWordWrap(True) #Prevents text from going off-screen
        self.sentimentReturn.setWordWrap(True)

        self.submitButton=QPushButton(self)
        self.inputLink=QLineEdit(self) #add input box
        self.plot_graph = pg.PlotWidget(self) #graph
        
        #input prompt
        
        self.linkPrompt.setText("Please enter a Youtube Video Link:")
        font = self.linkPrompt.font()
        font.setPointSize(15)
        self.linkPrompt.setFont(font)
        self.linkPrompt.setGeometry(10,-100,500,500) 
     
        #input link
        
        self.inputLink.setPlaceholderText("Enter a video link")
        self.inputLink.setGeometry(320,100,450,75) #(100 units from the top)
      
        #submit button
        self.submitButton.setGeometry(775, 100, 125,75)
        self.submitButton.setText("Submit")
        self.submitButton.clicked.connect(self.submit_button_clicked)

        #Plot Graph
#Get video title
    def videoTitle(self): 
           try:
             video= YouTube(self.inputLink.text())
             return video.title
           except Exception as e:
               return "Error, could not retrieve video title"
    #Get video title
    def videoID(self): 
           try:
             video= YouTube(self.inputLink.text())
             id=extract.video_id(self.inputLink.text())
             return id
           except Exception as e:
               return "Error, could not retrieve video title"

    def videoAuthor(self): 
           try:
             author= YouTube(self.inputLink.text())
             return author.author
           except Exception as e:
               return "Error, could not retrieve video title"



#Button actions
    def submit_button_clicked(self):
        #self.hideInputItems()
        video=self.videoID()
        author = self.videoAuthor()
        self.linkReturn.setText(f"From this video: {video} by {author}") 
        font = self.linkReturn.font()
        font.setPointSize(15)
        self.linkReturn.setFont(font)
        self.linkReturn.setGeometry(10,-200,700,500) 
        #Return comment sentiment
        self.sentimentReturn.setText(f"The general sentiment of the comments is:")
        font = self.sentimentReturn.font()
        font.setPointSize(15)
        self.sentimentReturn.setFont(font)
        self.sentimentReturn.setGeometry(10,-100,500,500) 
         #Hiding other stuff to prevent screen cluttering
        self.inputLink.hide()
        self.submitButton.hide()
        self.linkPrompt.hide()
        #show graph
        self.graphSentiment()

        #Temporary test for now using random stuff
    def graphSentiment(self):
        self.plot_graph.setGeometry(750,100,400,500)
        self.plot_graph.setBackground("w")
        item1 = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        item2 = [30, 32, 34, 32, 33, 31, 29, 32, 35, 30]
        self.plot_graph.plot(item1, item2)


    def center_on_screen(self):
        """Centers the window on the current screen."""
        # Get the geometry of the main window's frame
        frame_geometry = self.frameGeometry()

        # Get the screen containing the window and its available geometry
        screen_center = self.screen().availableGeometry().center()

        # Move the window's frame to the screen's center
        frame_geometry.moveCenter(screen_center)
        
        # Move the window itself to the top-left point of the moved frame
        self.move(frame_geometry.topLeft())
    


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
