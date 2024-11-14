import logo from './logo.svg';
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
          <img src={logo} className="App-logo" alt="logo" />
          <p>
            Edit <code>src/App.js</code> and save to reload.
          </p>
          <a
            className="App-link"
            href="https://reactjs.org"
            target="_blank"
            rel="noopener noreferrer"
          >
            Learn React
          </a>
        </header>
      </div>
    </ThemeProvider>
  );
}

export default App;


