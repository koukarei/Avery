import avery from './avery_robot.png';
import './App.css';
import { ThemeProvider } from '@mui/material/styles';
import { lightTheme } from './theme';
import ButtonAppBar from './AppBar';


function App() {
  return (
    <ThemeProvider theme={lightTheme}>
      <div className="App">
        <ButtonAppBar currentPage={"Leaderboard"}/>
        <header className="App-header">
          <img src={avery} className="App-logo" alt="logo" />
        </header>
      </div>
    </ThemeProvider>
  );
}

export default App;


