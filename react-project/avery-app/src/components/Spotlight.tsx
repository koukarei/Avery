import React, { useRef, useState } from "react";
import { Container, Box } from "@mui/material";
import "../App.css";
import Chat_Box from "./Chatbox";

const robotUrl = process.env.PUBLIC_URL + '/avery_robot.png';

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

type Props = {
  text: string;
}

const MainContentComponent: React.FC =() => {
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
    setOpacity(1);
  };

  const handleBlur = () => {
    setIsFocused(false);
    setOpacity(0);
  };

  const handleMouseEnter = () => {
    setOpacity(1);
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
      className="background-container"
    >
      <div
        className="background-effect"
        style={{
          opacity,
          background: `radial-gradient(600px circle at ${position.x}px ${position.y}px, #444445, transparent 30%)`,
        }}
      />
      <div className='background-img'></div>
      <Box className="Content">
        <Container className='Chatbox'>
          <Chat_Box robot={robotUrl} access_token="12"/>
        </Container>
        <Container className='Interaction'>
          
        </Container>
      </Box>
    </div>
    </div>
  );
};

export default MainContentComponent;