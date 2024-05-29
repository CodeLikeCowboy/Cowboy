import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import UnitTestList from '../components/UnitTestList';
import {getTestResults, submitTestResults} from './api';

import { UnitTest } from "../types/UnitTest";
import { ToastContainer } from 'react-toastify';
import Container from '@mui/material/Container';
import Button from '@mui/material/Button';


const TestResults: React.FC = () => {
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

  const handleSubmit = () => {
    const decisions = Object.keys(selectedTests).map((key) => ({
        id: unitTests[parseInt(key)].id,
        decision: selectedTests[parseInt(key)] ? 1 : 0
    }));

    console.log(decisions);
    submitTestResults(sessionId!, decisions);
  };

  return (
    <Container>
        <UnitTestList 
        initialTests={unitTests} 
        selectedTests={selectedTests} 
        onToggle={handleToggle} 
        />
        <Button 
            variant="contained" 
            color="primary" 
            onClick={handleSubmit} 
            fullWidth
            sx={{ mt: 3 }}
        >
        Submit
        </Button>
    <ToastContainer />
  </Container>

  );
};

export default TestResults;
