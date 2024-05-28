import React from 'react';
import { Checkbox, Card, CardContent, Typography, Box } from '@mui/material';

interface UnitTestItemProps {
  key: number;
  index: number;
  code: string;
  isChecked: boolean;
  onToggle: (index: number) => void;
  covImproved: number;
}

const UnitTestItem: React.FC<UnitTestItemProps> = ({ index, code, isChecked, onToggle, covImproved }) => {
  return (
    <Card variant="outlined" sx={{ mb: 2 }}>
      <CardContent>
        <Box display="flex" alignItems="center" mb={1}>
          <Checkbox checked={isChecked} onChange={() => onToggle(index)} />
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            Number {index}
          </Typography>
          <Typography variant="body2" sx={{ backgroundColor: '#333', color: '#fff', p: 1, borderRadius: 1 }}>
            {covImproved}%
          </Typography>
        </Box>
        <Box sx={{ backgroundColor: '#333', color: '#fff', p: 2, borderRadius: 1 }}>
          <pre>{code}</pre>
        </Box>
      </CardContent>
    </Card>
  );
};

export default UnitTestItem;
