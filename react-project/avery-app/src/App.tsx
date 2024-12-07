
import './App.css';
import  HorizontalLinearStepper  from './components/Steps';
import Chat_Box from './components/Chatbox';
import {cur_theme} from './styles/darktheme';
import styles from './styles/component';
import { createTheme, ThemeProvider } from "@mui/material";
import { Container, Box } from '@mui/material';
import { CardSpotlightEffect } from './components/Spotlight';

const robotUrl = process.env.PUBLIC_URL + '/avery_robot.png';

function App() {
  const theme = createTheme(cur_theme);
  return (
    <ThemeProvider theme={theme}>
      <div className={`App`}>
        <CardSpotlightEffect/>
        <HorizontalLinearStepper/>

      </div>
    </ThemeProvider>
    
  );
}

export default App;
