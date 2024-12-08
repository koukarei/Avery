import React from 'react';
import {Box,Container} from '@mui/material';
import Chat_Box from './Chatbox';
/** @jsxImportSource @emotion/react */
import { css } from "@emotion/react";
import { Theme } from '@mui/material';
import { StepContext } from '../providers/StepProvider';

const robotUrl = process.env.PUBLIC_URL + '/avery_robot.png';

type GameProps = {
    theme: Theme;
};

export default function Game({theme}: GameProps) {
    const {activeStep} = React.useContext(StepContext);
    
    return(
        <div css={ContentStyle}>
            <div css={ChatboxStyle}>
            <Chat_Box robot={robotUrl} access_token="12"/>
            </div>
            <div css={InteractionStyle}>

            </div>
        </div>
    )
}

const ContentStyle = css`
  position: absolute;
  display: flex;
  flex-direction: row;
  bottom: 5vh;
  height: 90%;
  width: 100%;
`;

const ChatboxStyle = (theme: Theme) => css`
  flex: 1;
  left: 2px;
  bottom: 0%;
  min-height: 90vh;
  background-color: pink;
`;

const InteractionStyle = (theme: Theme) => css`
  flex: 1;
  right: 2px;
  min-height: 90vh;
  background-color: lightblue;
`;
