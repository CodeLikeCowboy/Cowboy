import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import { CssBaseline } from '@mui/material';
import TestResults from './pages/TestResults';

import APIClient from 'api/APIClient';
import { readConfig } from 'config';
import { useEffect } from 'react';

const App: React.FC = () => {
  useEffect(() => {
    const initAPIClient = async () => {
      const config = await readConfig();
      new APIClient(config);
    };
    initAPIClient();
  }, []);

  return (
    <>
      <CssBaseline />
      <Router>
        <Routes>
          <Route path="/" element={<TestResults />} />
        </Routes>
      </Router>
    </>
  );
};
export default App;
