import React, { useState } from 'react';
import { Container, Box, Button } from '@mui/material';
import UnitTestItem from './UnitTestItem';
import { UnitTest } from '../types/API';

interface UnitTestListProps {
    initialTests: UnitTest[];
    selectedTests: { [key: number]: boolean };
    onToggle: (id: number) => void;
  }

const UnitTestList: React.FC<UnitTestListProps> = ({ initialTests, selectedTests, onToggle }) => {
  return (
    <Container>
      <Box>
        {initialTests.map((test, index) => (
          <UnitTestItem
            key={index}
            index={index}
            code={test.test_case}
            isChecked={!!selectedTests[index]}
            onToggle={onToggle}
            covImproved={test.cov_improved}
          />
        ))}
      </Box>
    </Container>
  );
};

export default UnitTestList;
