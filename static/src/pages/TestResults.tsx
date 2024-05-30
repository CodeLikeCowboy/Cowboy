import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import UnitTestList from '../components/UnitTestList';
import {getTestResults, submitTestResults} from './api';

import { UnitTest } from "../types/API";
import { ToastContainer } from 'react-toastify';
import Container from '@mui/material/Container';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';

import { useNavigate } from 'react-router-dom';

const TestResults: React.FC = () => {
  const navigate = useNavigate();
  const { sessionId } = useParams<{ sessionId: string }>();
  const [unitTests, setUnitTests] = useState<UnitTest[]>([]);
  const [selectedTests, setSelectedTests] = useState<{ [key: number]: boolean }>({});

  useEffect(() => {
    const fetchTestResults = async () => {
      try {
        const testResults = await getTestResults(sessionId!);
        setUnitTests(testResults);
        
        const selectedTests: {[index: number]: boolean} = {};
        testResults.forEach((test, index) => {
          selectedTests[index] = false;
        })
        setSelectedTests(selectedTests);
      } catch (error) {
        console.error('Failed to fetch test results:', error);
      }
    }
    fetchTestResults();
  }, []);

  const handleToggle = (index: number) => {
    setSelectedTests((prev) => {
      return {
        ...prev,
        [index]: !prev[index],
      };
    });
  };

  const handleSubmit = async () => {
    const decisions = Object.keys(selectedTests).map((key) => ({
        id: unitTests[parseInt(key)].id,
        decision: selectedTests[parseInt(key)] ? 1 : 0
    }));

    const res = await submitTestResults(sessionId!, decisions);
    navigate(`/compare-url/${encodeURIComponent(res.compare_url)}`);
  };

  return (
    <Container>
      <Box          
        width="60%"
        display="flex"
        flexDirection="column"
        // justifyContent="center"
        alignItems="center"
        sx={{ mt: 5 , mb: 5}}>

        <UnitTestList 
          initialTests={unitTests} 
          selectedTests={selectedTests} 
          onToggle={handleToggle} 
          />
          <Box width="50%" display="flex" justifyContent="flex-end">
            <Button 
                variant="contained" 
                color="primary" 
                onClick={handleSubmit} 
                fullWidth
                sx={{ mb: 3 }}
            >
              Submit
            </Button>
          </Box>
    </Box>
    <ToastContainer />
  </Container>

  );
};

export default TestResults;
