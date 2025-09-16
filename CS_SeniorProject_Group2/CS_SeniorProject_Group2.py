import sys
from PyQt6.QtWidgets import QApplication,QWidget,QLineEdit, QMainWindow, QLabel, QVBoxLayout, QPushButton

from pytubefix import YouTube,extract

#Starting window
class MainWindow(QMainWindow): 
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Comment Analyzer")
        self.resize(900, 500) # Set initial size
        self.center_on_screen() #Center the window, only needed for testing 

        #text 
        linkPrompt = QLabel(self)
        #All these have "self" next to them so they can be called outside of here.
        self.commentsAnalyzed= QLabel(self) #Return number of comments analyzed (Need some way to count them)
        self.sentimentReturn = QLabel(self) #Return sentiment summary
        self.linkReturn = QLabel(self) #Read link back to user
        self.linkReturn.setWordWrap(True) #Prevents text from going off-screen
        self.sentimentReturn.setWordWrap(True)

       #input prompt
        linkPrompt.setText("Please enter a Youtube Video Link:")
        font = linkPrompt.font()
        font.setPointSize(15)
        linkPrompt.setFont(font)
        linkPrompt.setGeometry(10,-100,500,500) 
     
        #input link
        self.inputLink=QLineEdit(self) #add input box
        self.inputLink.setPlaceholderText("Enter a video link")
        self.inputLink.setGeometry(320,100,450,75) #(100 units from the top)
      
        #submit button
        submitButton=QPushButton(self)
        submitButton.setGeometry(775, 100, 125,75)
        submitButton.setText("Submit")
        submitButton.clicked.connect(self.submit_button_clicked)

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
        video=self.videoID()
        author = self.videoAuthor()
        self.linkReturn.setText(f"From this video: {video} by {author}") 
        font = self.linkReturn.font()
        font.setPointSize(15)
        self.linkReturn.setFont(font)
        self.linkReturn.setGeometry(10,0,900,500) 
        #Return comment sentiment
        self.sentimentReturn.setText(f"The general sentiment of the comments is:")
        font = self.sentimentReturn.font()
        font.setPointSize(15)
        self.sentimentReturn.setFont(font)
        self.sentimentReturn.setGeometry(10,100,500,500) 


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
