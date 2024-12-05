import { ThemeOptions } from '@mui/material/styles';

export const darktheme: ThemeOptions = {
  palette: {
    mode: 'dark',
    primary: {
      main: '#dce5ff',
      light: '#f1f3f9',
      dark: '#afc3ff',
      contrastText: '#0f2b46',
    },
    secondary: {
      main: '#a1887f',
    },
    background: {
      default: '#0c0b0b',
      paper: '#484848',
    },
    text: {
      primary: 'rgba(255,255,255,0.87)',
      secondary: 'rgba(201,201,201,0.6)',
      disabled: 'rgba(115,115,115,0.38)',
    },
  },
};