import robot from './avery_robot.png';
import './App.css';
import  HorizontalLinearStepper  from './components/Steps';
import {darktheme} from './styles/darktheme';
import { createTheme, Snackbar, ThemeProvider } from "@mui/material";

function App() {
  const theme = createTheme(darktheme);
  return (
    <ThemeProvider theme={theme}>
      <div className="App">
      
        <div className='Stepper'><HorizontalLinearStepper /></div>

        <div className='Conversation_box'>
          
        </div>
      
        <img src={robot} className="Robot" alt="robot" />
      </div>
    </ThemeProvider>
    
  );
}

export default App;
