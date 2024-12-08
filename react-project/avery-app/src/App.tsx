
import './App.css';
import  HorizontalLinearStepper  from './components/Steps';
import cur_theme from './styles/darktheme';
import { createTheme, ThemeProvider } from "@mui/material";
import { Box } from '@mui/material';
import MainContentContainer from './components/background/Spotlight';
import LoginPage from "./components/LoginPage";
import Game from "./components/Game";
import { StepProvider } from './providers/StepProvider';

function App() {
  const theme = createTheme(cur_theme);
  return (
    <ThemeProvider theme={theme}>
      <Box className={`App`}>
        <MainContentContainer component={
          <StepProvider>
            <Game theme={theme}/>
          </StepProvider>
        } theme={theme}/>
        <StepProvider>
          <HorizontalLinearStepper theme={theme}/>
        </StepProvider>
      </Box>
    </ThemeProvider>
    
  );
}

export default App;
