
import './App.css';
import  HorizontalLinearStepper  from './components/Steps';
import cur_theme from './styles/darktheme';
import { createTheme, ThemeProvider } from "@mui/material";
import { Container, Box } from '@mui/material';
import MainContentComponent from './components/Spotlight';
import LoginPage from "./components/LoginPage";

function App() {
  const theme = createTheme(cur_theme);
  return (
    <ThemeProvider theme={theme}>
      <Box className={`App`}>
        <MainContentComponent/>
        <HorizontalLinearStepper/>
      </Box>
    </ThemeProvider>
    
  );
}

export default App;
