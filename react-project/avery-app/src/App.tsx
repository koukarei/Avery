
import './App.css';
import  HorizontalLinearStepper  from './components/Steps';
import cur_theme from './styles/darktheme';
import { createTheme, ThemeProvider } from "@mui/material";
import { Container, Box } from '@mui/material';
import MainContentContainer from './components/background/Spotlight';
import LoginPage from "./components/LoginPage";
import Chat_Box from "./components/Chatbox";
import { StepProvider } from './providers/StepProvider';

const robotUrl = process.env.PUBLIC_URL + '/avery_robot.png';

function App() {
  const theme = createTheme(cur_theme);
  return (
    <ThemeProvider theme={theme}>
      <Box className={`App`}>
        <MainContentContainer component={

          <Box className="Content">
            <Container className='Chatbox'>
              <Chat_Box robot={robotUrl} access_token="12"/>
            </Container>
            <Container className='Interaction'>
              
            </Container>
          </Box>

        } theme={theme}/>
        <StepProvider>
          <HorizontalLinearStepper theme={theme}/>
        </StepProvider>
      </Box>
    </ThemeProvider>
    
  );
}

export default App;
