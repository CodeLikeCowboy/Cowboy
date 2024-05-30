// src/CenteredCard.js
import React from 'react';
import { Card, CardContent, Typography, Container } from '@mui/material';

interface CenteredCardProps {
    title: string;
    text: string;
  }

function CenteredCard(props: CenteredCardProps) {
  return (
    <Container
      sx={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
      }}
    >
      <Card sx={{ maxWidth: 600, padding: 2, textAlign: 'justify' }}>
        <CardContent>
          <Typography variant="h4" component="div" gutterBottom>
            {props.title}
          </Typography>
          <Typography variant="body1" component="p">
            {props.text}
          </Typography>
        </CardContent>
      </Card>
    </Container>
  );
}

export default CenteredCard;
