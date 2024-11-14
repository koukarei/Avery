import { red } from '@mui/material/colors';
import { createTheme, responsiveFontSizes } from '@mui/material/styles';

// Light theme
let lightTheme = createTheme({
  palette: {
    primary: {
      main: '#0276aa',
    },
    secondary: {
      main: '#98F5F9',
    },
    error: {
      main: '#f44336',
    },
  },
});

lightTheme = responsiveFontSizes(lightTheme);

// Dark theme
let darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#000000',
    },
    secondary: {
      main: '#696969',
    },
    error: {
      main: '#FFE4E1',
    },
  },
});

darkTheme = responsiveFontSizes(darkTheme);

export { lightTheme, darkTheme };
