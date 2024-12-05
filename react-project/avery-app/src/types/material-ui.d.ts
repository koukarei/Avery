import { Theme, ThemeOptions } from "'@material-ui/core/styles/createMuiTheme";
import {
  Typography,
  TypographyOptions,
} from "@material-ui/core/styles/createTypography";

declare module "@material-ui/core/styles/createTheme" {
  interface Theme {
    headerHeight: number;
  }
  interface ThemeOptions {
    headerHeight: number;
  }
}
declare module "@material-ui/core/styles/createTypography" {
  interface Typography {
    size: (number) => number;
  }
  interface TypographyOptions {
    size: (number) => number;
  }
}

