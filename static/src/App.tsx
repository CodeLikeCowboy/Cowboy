import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import { CssBaseline } from '@mui/material';
import TestResults from './pages/TestResults';
import CompareURL from './pages/CompareURL';

const App: React.FC = () => {
  return (
    <>
      <CssBaseline />
      <Router>
        <Routes>
          <Route path="/test-results/:sessionId" element={<TestResults />} />
          <Route path="/compare-url/:compare_url" element={<CompareURL />} />
        </Routes>
      </Router>
    </>
  );
};


export default App;
