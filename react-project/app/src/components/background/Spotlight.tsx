import React, { Component, useRef, useState } from "react";
/** @jsxImportSource @emotion/react */
import { css } from "@emotion/react";
import { Theme } from '@mui/material';

const backgroundImgUrl = process.env.PUBLIC_URL + '/background.png';


function generateRandomColor(): string {
    const letters = '0123456789ABCDEF';
    let color = '#';
    for (let i = 0; i < 6; i++) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
}

function generateRandomGreyscale(): string {
    const value = Math.floor(Math.random() * 256);
    const hexValue = value.toString(16).padStart(2, '0');
    return `#${hexValue}${hexValue}${hexValue}`;
}

type MainContentProps = {
  component: React.ReactNode;
  theme: Theme;
};

const MainContentProvider : React.FC<MainContentProps> = ({
  component,
  theme,
}) => {
  const divRef = useRef(null);
  const [isFocused, setIsFocused] = useState(false);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [opacity, setOpacity] = useState(0);

  const handleMouseMove: React.MouseEventHandler<HTMLDivElement> = (e) => {
    if (!divRef.current || isFocused) return;

    const div = divRef.current as HTMLDivElement;
    const rect = div.getBoundingClientRect();

    setPosition({ x: e.clientX - rect.left, y: e.clientY - rect.top });
  };

  const handleFocus = () => {
    setIsFocused(true);
    setOpacity(0.7);
  };

  const handleBlur = () => {
    setIsFocused(false);
    setOpacity(0);
  };

  const handleMouseEnter = () => {
    setOpacity(0.7);
  };

  const handleMouseLeave = () => {
    setOpacity(0);
  };

  return (
    <div>
    <div
      ref={divRef}
      onMouseMove={handleMouseMove}
      onFocus={handleFocus}
      onBlur={handleBlur}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      css={backgroundContainerStyle}
    >
      <div
        css={backgroundEffectStyle}
        style={{
          opacity,
          background: `radial-gradient(600px circle at ${position.x}px ${position.y}px, ${theme.palette.secondary.light}, transparent 50%)`,
        }}
      />
      <div css={backgroundImgStyle}></div>
      {component}
    </div>
    </div>
  );
};

export default MainContentProvider;

const backgroundEffectStyle = css`
  position: absolute;
  pointer-events:none;
  opacity: 0;
  inset:-1px;
  transition: opacity 300ms;
`;

const backgroundImgStyle = css`
  position: absolute;
  top:0%;
  left:0%;
  height: 100%;
  width: 100%;
  background-size: stretch;
  background-image: url(${backgroundImgUrl});
`;

const backgroundContainerStyle = (theme: Theme) => css`
  position: absolute;
  overflow: hidden;
  top:0px;
  left:0px;
  height: 100%;
  width: 100%;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  background-color: ${theme.palette.background.default};
`;